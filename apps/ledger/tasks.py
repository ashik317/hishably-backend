import logging

from celery import shared_task
from django.db import transaction

from apps.shops.models import Shop

from .services import recompute_shop

log = logging.getLogger(__name__)


@shared_task
def recalc_balances():
    """Nightly safety net: rebuild every cached balance from the ledger and log mismatches."""
    mismatches = 0
    for pk in Shop.objects.values_list("pk", flat=True):
        with transaction.atomic():
            shop = Shop.objects.select_for_update().get(pk=pk)
            before = shop.current_balance
            recompute_shop(shop)
            if shop.current_balance != before:
                mismatches += 1
                log.error("Balance mismatch for shop %s: cached %s, ledger %s", shop.alias, before, shop.current_balance)
    return mismatches
