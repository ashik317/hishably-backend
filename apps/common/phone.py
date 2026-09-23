import re

from rest_framework.exceptions import ValidationError

BD_MOBILE = re.compile(r"^(?:\+?88)?(01[3-9]\d{8})$")


def normalize_bd_phone(raw: str) -> str:
    """Return a Bangladeshi mobile number as +8801XXXXXXXXX or raise ValidationError."""
    digits = re.sub(r"[\s\-()]", "", raw or "")
    match = BD_MOBILE.match(digits)
    if not match:
        raise ValidationError({"phone": "Enter a valid Bangladeshi mobile number, e.g. 01711-234567."})
    return "+88" + match.group(1)
