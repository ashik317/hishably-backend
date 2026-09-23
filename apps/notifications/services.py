from django.utils import timezone

from apps.shops.models import ShopShareLink

from .models import DEFAULT_TEMPLATES, SmsKind, SmsMessage, SmsTemplate
from .providers import sms_parts


def taka(value):
    return f"৳{value:,.0f}"


def template_for(business, kind):
    t = SmsTemplate.objects.filter(business=business, kind=kind).first()
    return t.body if t else DEFAULT_TEMPLATES.get(kind, "")


def render_for_shop(shop, kind, body=None, **extra):
    from django.conf import settings

    link = ShopShareLink.objects.filter(shop=shop, is_active=True).first() or ShopShareLink.objects.create(shop=shop)
    values = {
        "owner": shop.owner_name or shop.name, "shop": shop.name, "business": shop.business.name,
        "amount": taka(shop.current_balance), "balance": taka(shop.current_balance),
        "days": shop.days_overdue_base, "link": f"{settings.PUBLIC_BASE_URL}/p/{link.token}", **extra,
    }
    return (body or template_for(shop.business, kind)).format(**values)


def queue_sms(shop, kind, body=None, **extra):
    from .tasks import send_sms

    text = render_for_shop(shop, kind, body, **extra)
    msg = SmsMessage.objects.create(
        business=shop.business, shop=shop, phone=shop.phone, kind=kind, body=text, parts=sms_parts(text)
    )
    send_sms.delay(msg.pk)
    return msg


def recently_reminded(shop, days):
    since = timezone.now() - timezone.timedelta(days=days)
    return SmsMessage.objects.filter(shop=shop, kind__in=[SmsKind.REMINDER, SmsKind.OVERDUE], created_at__gte=since).exists()
