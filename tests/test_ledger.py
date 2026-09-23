from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.ledger.models import EntryType, LedgerEntry
from apps.ledger.services import post_entry, reverse_entry
from conftest import url


def post(client, biz, **data):
    return client.post(url(biz, "entries/"), data, format="json")


def test_sale_and_payment_update_balance(setup, client_for):
    c, biz, shop = client_for(setup["owner"]), setup["biz"], setup["shop"]
    r = post(c, biz, shop=str(shop.alias), type="sale", amount="20000", memo_no="M-1")
    assert r.status_code == 201, r.data
    assert r.data["shop_balance"] == "20000.00"
    r = post(c, biz, shop=str(shop.alias), type="payment", amount="7500", method="bkash")
    assert r.data["shop_balance"] == "12500.00"
    shop.refresh_from_db()
    assert shop.current_balance == Decimal("12500") and shop.last_payment_at is not None


def test_payment_requires_method(setup, client_for):
    r = post(client_for(setup["owner"]), setup["biz"], shop=str(setup["shop"].alias), type="payment", amount="100")
    assert r.status_code == 400 and "method" in r.data


def test_entries_are_append_only(setup):
    e = post_entry(shop=setup["shop"], entry_type=EntryType.SALE, amount=1000, user=setup["owner"])
    e.amount = Decimal("5")
    with pytest.raises(ValidationError):
        e.save()
    with pytest.raises(ValidationError):
        e.delete()


def test_reversal_restores_balance_and_cannot_repeat(setup, client_for):
    owner, biz, shop = setup["owner"], setup["biz"], setup["shop"]
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=10000, user=owner)
    wrong = post_entry(shop=shop, entry_type=EntryType.SALE, amount=9999, user=owner)
    c = client_for(owner)
    r = c.post(url(biz, f"entries/{wrong.pk}/reverse/"), {"reason": "Wrong amount"}, format="json")
    assert r.status_code == 201, r.data
    shop.refresh_from_db()
    assert shop.current_balance == Decimal("10000")
    assert c.post(url(biz, f"entries/{wrong.pk}/reverse/"), {"reason": "again"}, format="json").status_code == 400
    assert LedgerEntry.objects.filter(shop=shop).count() == 3  # nothing deleted


def test_rep_cannot_reverse(setup, client_for):
    e = post_entry(shop=setup["shop"], entry_type=EntryType.SALE, amount=1000, user=setup["owner"])
    r = client_for(setup["rep"]).post(url(setup["biz"], f"entries/{e.pk}/reverse/"), {"reason": "x"}, format="json")
    assert r.status_code == 403


def test_idempotency_key_prevents_double_posting(setup, client_for):
    c, biz, shop = client_for(setup["owner"]), setup["biz"], setup["shop"]
    data = {"shop": str(shop.alias), "type": "sale", "amount": "5000"}
    r1 = c.post(url(biz, "entries/"), data, format="json", HTTP_IDEMPOTENCY_KEY="abc-123")
    r2 = c.post(url(biz, "entries/"), data, format="json", HTTP_IDEMPOTENCY_KEY="abc-123")
    assert r1.data["id"] == r2.data["id"]
    shop.refresh_from_db()
    assert shop.current_balance == Decimal("5000")


def test_rep_blocked_over_credit_limit_but_owner_allowed(setup, client_for):
    biz, shop = setup["biz"], setup["shop"]  # limit 50,000
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=45000, user=setup["owner"])
    r = post(client_for(setup["rep"]), biz, shop=str(shop.alias), type="sale", amount="10000")
    assert r.status_code == 400 and "limit" in str(r.data["amount"])
    r = post(client_for(setup["owner"]), biz, shop=str(shop.alias), type="sale", amount="10000")
    assert r.status_code == 201 and r.data["shop_balance"] == "55000.00"


def test_accountant_is_read_only(setup, client_for):
    c = client_for(setup["accountant"])
    assert c.get(url(setup["biz"], "entries/")).status_code == 200
    assert post(c, setup["biz"], shop=str(setup["shop"].alias), type="sale", amount="100").status_code == 403


def test_ledger_running_balance(setup, client_for):
    shop, owner = setup["shop"], setup["owner"]
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=1000, user=owner)
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=500, user=owner)
    post_entry(shop=shop, entry_type=EntryType.PAYMENT, amount=300, user=owner, method="cash")
    rows = client_for(owner).get(url(setup["biz"], f"shops/{shop.alias}/ledger/")).data["results"]
    assert [r["running_balance"] for r in rows] == ["1200.00", "1500.00", "1000.00"]  # newest first


def test_fifo_due_since(setup):
    from datetime import timedelta

    from django.utils import timezone

    shop, owner, today = setup["shop"], setup["owner"], timezone.localdate()
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=1000, user=owner, entry_date=today - timedelta(days=40))
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=1000, user=owner, entry_date=today - timedelta(days=10))
    shop.refresh_from_db()
    assert shop.due_since == today - timedelta(days=40)
    post_entry(shop=shop, entry_type=EntryType.PAYMENT, amount=1000, user=owner, method="cash")
    shop.refresh_from_db()
    assert shop.due_since == today - timedelta(days=10)  # oldest memo is now paid
    post_entry(shop=shop, entry_type=EntryType.PAYMENT, amount=1000, user=owner, method="cash")
    shop.refresh_from_db()
    assert shop.due_since is None and shop.status == "clear"


def test_reverse_service_needs_reason(setup):
    e = post_entry(shop=setup["shop"], entry_type=EntryType.SALE, amount=100, user=setup["owner"])
    from rest_framework.exceptions import ValidationError as DRFValidationError
    with pytest.raises(DRFValidationError):
        reverse_entry(entry=e, user=setup["owner"], reason="")
