import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import AliasModel, TimeStampedModel


class Area(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="areas")
    name = models.CharField(max_length=80)
    assigned_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="rep_areas"
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [models.UniqueConstraint(fields=["business", "name"], name="unique_area_name")]

    def __str__(self):
        return self.name


class Shop(AliasModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="shops")
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="shops")
    name = models.CharField(max_length=150)
    owner_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=16, blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to="shops/", blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("50000"))
    due_days = models.PositiveSmallIntegerField(default=15)
    is_active = models.BooleanField(default=True)

    # Cached values — only ever written by apps.ledger.services inside a locked transaction.
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    last_payment_at = models.DateField(null=True, blank=True)
    due_since = models.DateField(null=True, blank=True)  # date of the oldest unpaid sale (FIFO)

    class Meta:
        indexes = [
            models.Index(fields=["business", "area"]),
            models.Index(fields=["business", "current_balance"]),
            models.Index(fields=["business", "due_since"]),
        ]

    def __str__(self):
        return self.name

    @property
    def days_overdue_base(self):
        return (timezone.localdate() - self.due_since).days if self.due_since else 0

    @property
    def status(self):
        if self.current_balance > self.credit_limit:
            return "over_limit"
        if self.due_since and self.days_overdue_base > self.due_days:
            return "overdue"
        if self.current_balance <= 0:
            return "clear"
        return "good"


def _token():
    return secrets.token_urlsafe(12)


class ShopShareLink(TimeStampedModel):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="share_links")
    token = models.CharField(max_length=32, unique=True, default=_token)
    expires_at = models.DateTimeField(null=True, blank=True)
    allow_payment = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    @property
    def is_valid(self):
        return self.is_active and (self.expires_at is None or self.expires_at > timezone.now())
