from celery import shared_task
from django.utils import timezone

from .models import ReminderRule, SmsKind, SmsMessage
from .providers import get_sms_provider
from .services import queue_sms, recently_reminded


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms(self, message_id):
    msg = SmsMessage.objects.get(pk=message_id)
    if msg.status == SmsMessage.Status.SENT:
        return
    provider = get_sms_provider()
    try:
        result = provider.send(msg.phone, msg.body)
    except Exception as exc:  # network errors etc.
        msg.error = str(exc)[:255]
        msg.save(update_fields=["error", "updated_at"])
        raise self.retry(exc=exc)
    msg.provider, msg.provider_id = provider.name, result.provider_id
    msg.status = SmsMessage.Status.SENT if result.ok else SmsMessage.Status.FAILED
    msg.error = result.error
    msg.sent_at = timezone.now()
    msg.save()


@shared_task
def run_reminder_rules():
    """Daily: remind shops that are about to be due, or are overdue."""
    sent = 0
    for rule in ReminderRule.objects.filter(is_active=True).select_related("business"):
        shops = rule.business.shops.filter(is_active=True, current_balance__gt=0, due_since__isnull=False).exclude(phone="")
        for shop in shops:
            days = shop.days_overdue_base
            if recently_reminded(shop, rule.repeat_every_days):
                continue
            if rule.remind_on_overdue and days > shop.due_days:
                queue_sms(shop, SmsKind.OVERDUE)
                sent += 1
            elif shop.due_days - rule.days_before_due <= days <= shop.due_days:
                queue_sms(shop, SmsKind.REMINDER)
                sent += 1
    return sent
