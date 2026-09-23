"""All money changes go through this module.

Every posting runs in one DB transaction that locks the shop row, so two requests
(e.g. a rep and the owner) can never compute the balance from the same stale value.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Membership, Role
from apps.shops.models import Shop

from .models import DIRECTION, AuditLog, EntryType, LedgerEntry


class OverLimitError(ValidationError):
    default_code = "over_limit"


def _fifo_due_since(shop):
    """Date of the oldest sale that isn't fully covered by payments/credits (FIFO)."""
    active = LedgerEntry.objects.filter(shop=shop, reversed_by__isnull=True).exclude(type=EntryType.REVERSAL)
    credits = active.filter(direction=-1).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    for debit in active.filter(direction=1).order_by("entry_date", "id").only("amount", "entry_date"):
        if credits >= debit.amount:
            credits -= debit.amount
            continue
        return debit.entry_date
    return None


def recompute_shop(shop):
    """Rebuild cached fields from the ledger. Call inside a transaction holding the shop lock."""
    shop.current_balance = sum((e.signed_amount for e in shop.entries.all()), Decimal("0"))
    last_pay = (
        shop.entries.filter(type=EntryType.PAYMENT, reversed_by__isnull=True).order_by("-entry_date", "-id").first()
    )
    shop.last_payment_at = last_pay.entry_date if last_pay else None
    shop.due_since = _fifo_due_since(shop) if shop.current_balance > 0 else None
    shop.save(update_fields=["current_balance", "last_payment_at", "due_since", "updated_at"])
    return shop


def _audit(business, user, action, entry, **data):
    AuditLog.objects.create(
        business=business, user=user, action=action, object_type="ledger_entry", object_id=str(entry.pk),
        data={"shop": str(entry.shop.alias), "type": entry.type, "amount": str(entry.amount), **data},
    )


def post_entry(*, shop, entry_type, amount, user, entry_date=None, memo_no="", method="", note="",
               source="manual", idempotency_key=None, allow_over_limit=False, photo=None):
    if entry_type not in DIRECTION:
        raise ValidationError({"type": "Unsupported entry type."})
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be greater than zero."})

    with transaction.atomic():
        shop = Shop.objects.select_for_update().select_related("business").get(pk=shop.pk)
        business = shop.business

        if idempotency_key:
            existing = LedgerEntry.objects.filter(business=business, idempotency_key=idempotency_key).first()
            if existing:
                return existing  # same request retried (double tap, bad network) — don't post twice

        direction = DIRECTION[entry_type]
        new_balance = shop.current_balance + direction * amount
        if direction > 0 and entry_type == EntryType.SALE and new_balance > shop.credit_limit and not allow_over_limit:
            if business.require_owner_approval_over_limit:
                role = Membership.objects.filter(business=business, user=user).values_list("role", flat=True).first()
                if role not in (Role.OWNER, Role.MANAGER):
                    raise OverLimitError({
                        "amount": f"This sale takes {shop.name} to ৳{new_balance:,.0f}, over its limit of "
                                  f"৳{shop.credit_limit:,.0f}. The owner or a manager must approve it.",
                        "code": "over_limit",
                    })

        try:
            entry = LedgerEntry.objects.create(
                business=business, shop=shop, type=entry_type, direction=direction, amount=amount,
                entry_date=entry_date or timezone.localdate(), memo_no=memo_no, method=method or "",
                note=note, source=source, idempotency_key=idempotency_key or None, created_by=user,
                photo=photo,
            )
        except IntegrityError:
            return LedgerEntry.objects.get(business=business, idempotency_key=idempotency_key)

        recompute_shop(shop)
        _audit(business, user, "entry.created", entry)
        return entry


def reverse_entry(*, entry, user, reason):
    if not reason:
        raise ValidationError({"reason": "A reason is required."})
    with transaction.atomic():
        shop = Shop.objects.select_for_update().get(pk=entry.shop_id)
        entry = LedgerEntry.objects.select_for_update().get(pk=entry.pk)
        if entry.type == EntryType.REVERSAL:
            raise ValidationError({"detail": "A reversal can't be reversed."})
        if LedgerEntry.objects.filter(reverses=entry).exists():
            raise ValidationError({"detail": "This entry is already reversed."})
        reversal = LedgerEntry.objects.create(
            business=entry.business, shop=shop, type=EntryType.REVERSAL, direction=-entry.direction,
            amount=entry.amount, entry_date=timezone.localdate(), note=reason, reverses=entry, created_by=user,
        )
        recompute_shop(shop)
        _audit(entry.business, user, "entry.reversed", entry, reason=reason, reversal_id=reversal.pk)
        return reversal
