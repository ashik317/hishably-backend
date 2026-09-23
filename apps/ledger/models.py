from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class EntryType(models.TextChoices):
    OPENING = "opening", "Opening balance"
    SALE = "sale", "Sale on credit"
    PAYMENT = "payment", "Payment"
    RETURN = "return", "Return"
    DISCOUNT = "discount", "Discount"
    WRITE_OFF = "write_off", "Write-off"
    REVERSAL = "reversal", "Reversal"


# +1 increases what the shop owes, -1 decreases it
DIRECTION = {
    EntryType.OPENING: 1,
    EntryType.SALE: 1,
    EntryType.PAYMENT: -1,
    EntryType.RETURN: -1,
    EntryType.DISCOUNT: -1,
    EntryType.WRITE_OFF: -1,
}


class PaymentMethod(models.TextChoices):
    NONE = "", "—"
    CASH = "cash", "Cash"
    BKASH = "bkash", "bKash"
    NAGAD = "nagad", "Nagad"
    BANK = "bank", "Bank transfer"
    CHEQUE = "cheque", "Cheque"


class EntrySource(models.TextChoices):
    MANUAL = "manual", "Manual"
    VOICE = "voice", "Voice (AI)"
    OCR = "ocr", "Photo (AI)"
    ONLINE = "online", "Online payment"
    IMPORT = "import", "Import"


class LedgerEntry(models.Model):
    """Append-only. Never update or delete a row; correct mistakes with a reversal entry."""

    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="entries")
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="entries")
    type = models.CharField(max_length=10, choices=EntryType.choices)
    direction = models.SmallIntegerField()  # +1 or -1
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    entry_date = models.DateField()
    memo_no = models.CharField(max_length=40, blank=True)
    method = models.CharField(max_length=10, choices=PaymentMethod.choices, blank=True, default="")
    note = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to="memos/", blank=True, null=True)
    source = models.CharField(max_length=10, choices=EntrySource.choices, default=EntrySource.MANUAL)
    reverses = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversed_by")
    idempotency_key = models.CharField(max_length=64, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["entry_date", "id"]
        indexes = [
            models.Index(fields=["business", "shop", "entry_date"]),
            models.Index(fields=["business", "entry_date"]),
            models.Index(fields=["business", "created_by", "entry_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "idempotency_key"], name="unique_idempotency_key",
                condition=models.Q(idempotency_key__isnull=False),
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="entry_amount_positive"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Ledger entries are append-only. Use a reversal instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Ledger entries can't be deleted. Use a reversal instead.")

    @property
    def signed_amount(self):
        return self.amount * self.direction

    @property
    def is_reversed(self):
        return hasattr(self, "reversed_by")


class AuditLog(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    action = models.CharField(max_length=40)
    object_type = models.CharField(max_length=40)
    object_id = models.CharField(max_length=40)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["business", "created_at"])]
