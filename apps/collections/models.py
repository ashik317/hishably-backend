from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class CollectionVisit(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="visits")
    rep = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits")
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="visits")
    visited_at = models.DateTimeField()
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    payment = models.OneToOneField("ledger.LedgerEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="visit")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-visited_at"]


class CashHandover(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        DIFFERENCE = "difference", "Difference"

    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="handovers")
    rep = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="handovers")
    date = models.DateField()
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2)
    handed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["business", "rep", "date"], name="one_handover_per_rep_day")]

    @property
    def difference(self):
        return None if self.handed_amount is None else self.handed_amount - self.expected_amount
