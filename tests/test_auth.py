import pytest
from rest_framework.test import APIClient

from apps.accounts.models import OTPCode, User


@pytest.mark.django_db
def test_otp_login_creates_user_and_returns_tokens():
    c = APIClient()
    r = c.post("/api/v1/auth/otp/send/", {"phone": "01711-234567"})
    assert r.status_code == 200
    assert r.data["phone"] == "+8801711234567"
    code = r.data["debug_code"]

    r = c.post("/api/v1/auth/otp/verify/", {"phone": "8801711234567", "code": code, "name": "Karim"})
    assert r.status_code == 200, r.data
    assert r.data["is_new"] is True and "access" in r.data
    assert User.objects.get(phone="+8801711234567").name == "Karim"

    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    assert c.get("/api/v1/auth/me/").data["phone"] == "+8801711234567"


@pytest.mark.django_db
def test_wrong_code_and_code_reuse_rejected():
    c = APIClient()
    code = c.post("/api/v1/auth/otp/send/", {"phone": "01711234567"}).data["debug_code"]
    wrong = "000000" if code != "000000" else "111111"
    assert c.post("/api/v1/auth/otp/verify/", {"phone": "01711234567", "code": wrong}).status_code == 400
    assert c.post("/api/v1/auth/otp/verify/", {"phone": "01711234567", "code": code}).status_code == 200
    assert c.post("/api/v1/auth/otp/verify/", {"phone": "01711234567", "code": code}).status_code == 400


@pytest.mark.django_db
def test_invalid_phone_rejected():
    r = APIClient().post("/api/v1/auth/otp/send/", {"phone": "12345"})
    assert r.status_code == 400


@pytest.mark.django_db
def test_otp_locks_after_max_attempts(settings):
    code = OTPCode.issue("+8801711234567")
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        OTPCode.verify("+8801711234567", "999999" if code != "999999" else "888888")
    assert OTPCode.verify("+8801711234567", code) is False
