import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError("Phone is required")
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Language(models.TextChoices):
        BANGLA = "bn", "Bangla"
        ENGLISH = "en", "English"

    phone = models.CharField(max_length=16, unique=True)  # +8801XXXXXXXXX
    name = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.BANGLA)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.name or self.phone


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
        cls.objects.filter(phone=phone, used=False).update(used=True)  # only the newest code works
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
        if secrets.compare_digest(otp.code_hash, _hash(code)):
            otp.used = True
        otp.save(update_fields=["attempts", "used"])
        return otp.used
