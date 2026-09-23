import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.enums import Language, NameTitleChoices
from apps.accounts.utils import profile_image_upload_path
from apps.common.phone import normalize_bd_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone=None, email=None, password=None, **extra):
        if not phone:
            raise ValueError("A phone number is required")

        phone = normalize_bd_phone(phone)
        email = self.normalize_email(email) if email else None

        user = self.model(phone=phone, email=email, **extra)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        if not email:
            raise ValueError("Superuser must have an email")
        if not extra.get("phone"):
            raise ValueError("Superuser must have a phone number")
        if not extra.get("first_name"):
            raise ValueError("Superuser must have a first name")
        if not extra.get("last_name"):
            raise ValueError("Superuser must have a last name")

        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)

        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email=email, password=password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=16, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    title = models.CharField(max_length=64, choices=NameTitleChoices.choices, blank=True, null=True)
    first_name = models.CharField(max_length=60)
    middle_name = models.CharField(max_length=60, blank=True, null=True)
    last_name = models.CharField(max_length=60)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.BANGLA)
    current_address = models.CharField(max_length=255, blank=True, null=True)
    ni_number = models.CharField(max_length=9, blank=True, null=True)
    profile_image = models.ImageField(upload_to=profile_image_upload_path, blank=True, null=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.name or self.email or self.phone

    @property
    def name(self):
        parts = [
            self.get_title_display() if self.title else None,
            self.first_name,
            self.middle_name,
            self.last_name,
        ]
        return " ".join(part for part in parts if part)

    @name.setter
    def name(self, value):
        parts = (value or "").split()
        self.first_name = parts[0] if parts else ""
        self.last_name = parts[-1] if len(parts) > 1 else ""
        self.middle_name = " ".join(parts[1:-1])

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.first_name


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class OTPCode(models.Model):
    phone = models.CharField(max_length=16, db_index=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, phone: str) -> str:
        cls.objects.filter(phone=phone, used=False).update(used=True)
        code = f"{secrets.randbelow(10**6):06d}"
        cls.objects.create(
            phone=phone,
            code_hash=_hash(code),
            expires_at=timezone.now() + timedelta(minutes=settings.OTP_TTL_MINUTES),
        )
        return code

    @classmethod
    def verify(cls, phone: str, code: str) -> bool:
        otp = cls.objects.filter(phone=phone, used=False).order_by("-created_at").first()

        if not otp or otp.expires_at < timezone.now() or otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            return False

        otp.attempts += 1
        is_valid = secrets.compare_digest(otp.code_hash, _hash(code))
        if is_valid:
            otp.used = True

        otp.save(update_fields=["attempts", "used"])
        return is_valid