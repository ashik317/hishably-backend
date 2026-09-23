from django.conf import settings
from django.db import models

from apps.common.models import AliasModel, TimeStampedModel


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    MANAGER = "manager", "Manager"
    REP = "rep", "Sales rep"
    ACCOUNTANT = "accountant", "Accountant"


class Business(AliasModel):
    class TradeType(models.TextChoices):
        FMCG = "fmcg", "FMCG / Grocery"
        PHARMA = "pharma", "Pharma"
        HARDWARE = "hardware", "Hardware"
        ELECTRONICS = "electronics", "Electronics"
        FOOD_GRAIN = "food_grain", "Rice / Food grain"
        OTHER = "other", "Other"

    class Plan(models.TextChoices):
        FREE = "free", "Free"
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"
        BUSINESS = "business", "Business"

    name = models.CharField(max_length=150)
    trade_type = models.CharField(max_length=20, choices=TradeType.choices, default=TradeType.FMCG)
    phone = models.CharField(max_length=16, blank=True)
    address = models.CharField(max_length=255, blank=True)
    trade_licence = models.CharField(max_length=60, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    default_credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    default_due_days = models.PositiveSmallIntegerField(default=15)
    require_owner_approval_over_limit = models.BooleanField(default=True)
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_businesses")

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.REP)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "user"], name="unique_member")]

    def __str__(self):
        return f"{self.user} @ {self.business} ({self.role})"
