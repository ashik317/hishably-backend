from rest_framework import serializers

from .models import ReminderRule, SmsKind, SmsMessage, SmsTemplate


class SmsMessageSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True, default=None)

    class Meta:
        model = SmsMessage
        fields = ["id", "shop_name", "phone", "kind", "body", "parts", "status", "error", "sent_at", "created_at"]


class RemindSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[SmsKind.REMINDER, SmsKind.OVERDUE, SmsKind.CUSTOM], default=SmsKind.REMINDER)
    body = serializers.CharField(required=False, max_length=600)


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsTemplate
        fields = ["kind", "body"]


class ReminderRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderRule
        fields = ["is_active", "days_before_due", "remind_on_overdue", "repeat_every_days", "send_receipts"]
