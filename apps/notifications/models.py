from django.db import models

from apps.common.models import TimeStampedModel


class SmsKind(models.TextChoices):
    REMINDER = "reminder", "Reminder"
    OVERDUE = "overdue", "Overdue notice"
    RECEIPT = "receipt", "Payment receipt"
    CUSTOM = "custom", "Custom"


DEFAULT_TEMPLATES = {
    SmsKind.REMINDER: "প্রিয় {owner}, {business}-এ আপনার বাকি {amount}। পরিশোধ করুন: {link}",
    SmsKind.OVERDUE: "প্রিয় {owner}, {business}-এ আপনার {amount} বাকি {days} দিন ধরে পড়ে আছে। দয়া করে পরিশোধ করুন: {link}",
    SmsKind.RECEIPT: "{business}: আপনার {amount} পেমেন্ট পাওয়া গেছে। বর্তমান বাকি {balance}। ধন্যবাদ!",
}


class SmsTemplate(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="sms_templates")
    kind = models.CharField(max_length=10, choices=SmsKind.choices)
    body = models.TextField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "kind"], name="one_template_per_kind")]


class SmsMessage(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="sms_messages")
    shop = models.ForeignKey("shops.Shop", on_delete=models.SET_NULL, null=True, blank=True, related_name="sms_messages")
    phone = models.CharField(max_length=16)
    kind = models.CharField(max_length=10, choices=SmsKind.choices, default=SmsKind.CUSTOM)
    body = models.TextField()
    parts = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.QUEUED)
    provider = models.CharField(max_length=20, blank=True)
    provider_id = models.CharField(max_length=80, blank=True)
    error = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["business", "created_at"])]


class ReminderRule(TimeStampedModel):
    business = models.OneToOneField("businesses.Business", on_delete=models.CASCADE, related_name="reminder_rule")
    is_active = models.BooleanField(default=True)
    days_before_due = models.PositiveSmallIntegerField(default=3)
    remind_on_overdue = models.BooleanField(default=True)
    repeat_every_days = models.PositiveSmallIntegerField(default=7)
    send_receipts = models.BooleanField(default=True)
