"""SMS providers behind one interface, so switching gateways never touches business code."""
import logging

from django.conf import settings

log = logging.getLogger("hishably.sms")


class SmsResult:
    def __init__(self, ok, provider_id="", error=""):
        self.ok, self.provider_id, self.error = ok, provider_id, error


class BaseSmsProvider:
    name = "base"

    def send(self, phone: str, body: str) -> SmsResult:
        raise NotImplementedError


class ConsoleSmsProvider(BaseSmsProvider):
    """Development: prints the SMS instead of sending it."""

    name = "console"
    outbox = []  # handy in tests

    def send(self, phone, body):
        log.info("SMS to %s: %s", phone, body)
        print(f"[SMS → {phone}] {body}")
        self.outbox.append((phone, body))
        return SmsResult(True, provider_id=f"console-{len(self.outbox)}")


class HttpSmsProvider(BaseSmsProvider):
    """Template for a BD gateway (SSL Wireless, Alpha SMS, BulkSMSBD…). Fill in their API details."""

    name = "http"

    def send(self, phone, body):
        raise NotImplementedError("Add your SMS gateway's API call here.")


PROVIDERS = {"console": ConsoleSmsProvider, "http": HttpSmsProvider}


def get_sms_provider() -> BaseSmsProvider:
    return PROVIDERS[settings.SMS_PROVIDER]()


def sms_parts(body: str) -> int:
    """Unicode (Bangla) SMS: 70 chars for one part, 67 per part when split."""
    unicode = any(ord(c) > 127 for c in body)
    single, multi = (70, 67) if unicode else (160, 153)
    return 1 if len(body) <= single else -(-len(body) // multi)
