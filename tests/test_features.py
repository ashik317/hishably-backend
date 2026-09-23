from decimal import Decimal

from apps.ledger.models import EntryType
from apps.ledger.services import post_entry
from apps.notifications.models import SmsMessage
from apps.notifications.providers import sms_parts
from conftest import url


def test_dashboard_numbers(setup, client_for):
    shop, owner = setup["shop"], setup["owner"]
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=20000, user=owner)
    post_entry(shop=shop, entry_type=EntryType.PAYMENT, amount=5000, user=owner, method="cash")
    d = client_for(owner).get(url(setup["biz"], "dashboard/")).data
    assert d["total_due"] == "15000.00"
    assert d["today_sales"] == "20000.00" and d["today_collections"] == "5000.00"
    assert d["top_dues"][0]["name"] == "Rahman Store"
    assert d["aging"]["0_15"]["shops"] == 1


def test_remind_shop_sends_bangla_sms_with_link(setup, client_for):
    post_entry(shop=setup["shop"], entry_type=EntryType.SALE, amount=8500, user=setup["owner"])
    r = client_for(setup["owner"]).post(url(setup["biz"], f"shops/{setup['shop'].alias}/remind/"), {}, format="json")
    assert r.status_code == 201, r.data
    msg = SmsMessage.objects.get()
    assert msg.status == "sent" and "৳8,500" in msg.body and "/p/" in msg.body


def test_public_ledger_link(setup, client_for):
    post_entry(shop=setup["shop"], entry_type=EntryType.SALE, amount=3000, user=setup["owner"])
    r = client_for(setup["owner"]).post(url(setup["biz"], f"shops/{setup['shop'].alias}/share-links/"), {}, format="json")
    token = r.data["token"]
    from rest_framework.test import APIClient
    pub = APIClient().get(f"/api/v1/public/ledger/{token}/")
    assert pub.status_code == 200 and pub.data["current_balance"] == "3000.00"
    assert APIClient().get("/api/v1/public/ledger/not-a-token/").status_code == 404


def test_rep_visit_and_cash_handover(setup, client_for):
    rep_c, owner_c, biz, shop = client_for(setup["rep"]), client_for(setup["owner"]), setup["biz"], setup["shop"]
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=10000, user=setup["owner"])
    r = rep_c.post(url(biz, "visits/"), {"shop": str(shop.alias), "amount": "4000", "method": "cash"}, format="json")
    assert r.status_code == 201, r.data
    shop.refresh_from_db()
    assert shop.current_balance == Decimal("6000")
    h = rep_c.post(url(biz, "handovers/"), {}, format="json").data
    assert h["expected_amount"] == "4000.00" and h["status"] == "pending"
    r = owner_c.post(url(biz, f"handovers/{h['id']}/confirm/"), {"handed_amount": "3500"}, format="json")
    assert r.data["status"] == "difference" and r.data["difference"] == "-500.00"


def test_sms_parts():
    assert sms_parts("hello") == 1
    assert sms_parts("ক" * 70) == 1 and sms_parts("ক" * 71) == 2
