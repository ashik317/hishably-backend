from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import Membership, Role
from apps.common.tenancy import BusinessScopedMixin
from apps.ledger.models import EntryType, LedgerEntry
from apps.shops.views import shops_for

BUCKETS = [("0_15", 0, 15), ("16_30", 16, 30), ("31_60", 31, 60), ("60_plus", 61, 10**6)]


def _money(v):
    return str(Decimal(v or 0).quantize(Decimal("0.01")))


@extend_schema(responses=OpenApiTypes.OBJECT)
class DashboardView(BusinessScopedMixin, APIView):
    def get(self, request, business_alias):
        today = timezone.localdate()
        shops = list(shops_for(self).filter(is_active=True))
        entries = LedgerEntry.objects.filter(business=self.business, shop__in=[s.pk for s in shops], reversed_by__isnull=True)
        active = entries.exclude(type=EntryType.REVERSAL)

        overdue = [s for s in shops if s.status == "overdue" or (s.due_since and s.days_overdue_base > s.due_days)]
        todays = active.filter(entry_date=today)
        days = int(request.query_params.get("days", 14))
        start = today - timedelta(days=days - 1)
        daily = (
            active.filter(entry_date__gte=start, type__in=[EntryType.SALE, EntryType.PAYMENT])
            .values("entry_date", "type").annotate(total=Sum("amount"))
        )
        series = {(start + timedelta(d)).isoformat(): {"sales": "0", "collections": "0"} for d in range(days)}
        for row in daily:
            key = "sales" if row["type"] == EntryType.SALE else "collections"
            series[row["entry_date"].isoformat()][key] = str(row["total"])

        top = sorted(shops, key=lambda s: s.current_balance, reverse=True)[:10]
        return Response({
            "total_due": _money(sum((max(s.current_balance, 0) for s in shops), Decimal("0"))),
            "overdue_amount": _money(sum((s.current_balance for s in overdue), Decimal("0"))),
            "overdue_shops": len(overdue),
            "over_limit_shops": sum(1 for s in shops if s.current_balance > s.credit_limit),
            "today_sales": _money(todays.filter(type=EntryType.SALE).aggregate(s=Sum("amount"))["s"]),
            "today_sale_count": todays.filter(type=EntryType.SALE).count(),
            "today_collections": _money(todays.filter(type=EntryType.PAYMENT).aggregate(s=Sum("amount"))["s"]),
            "series": [{"date": k, **v} for k, v in series.items()],
            "top_dues": [
                {"alias": str(s.alias), "name": s.name, "area": s.area.name if s.area else None,
                 "balance": _money(s.current_balance), "credit_limit": _money(s.credit_limit), "status": s.status}
                for s in top
            ],
            "aging": aging(shops),
        })


def aging(shops):
    out = {k: {"amount": Decimal("0"), "shops": 0} for k, _, _ in BUCKETS}
    for s in shops:
        if s.current_balance <= 0:
            continue
        d = s.days_overdue_base
        for key, lo, hi in BUCKETS:
            if lo <= d <= hi:
                out[key]["amount"] += s.current_balance
                out[key]["shops"] += 1
    return {k: {"amount": _money(v["amount"]), "shops": v["shops"]} for k, v in out.items()}


@extend_schema(responses=OpenApiTypes.OBJECT)
class AgingReportView(BusinessScopedMixin, APIView):
    allowed_roles = {Role.OWNER, Role.MANAGER, Role.ACCOUNTANT}

    def get(self, request, business_alias):
        shops = [s for s in shops_for(self).filter(current_balance__gt=0)]
        rows = sorted(
            ({"alias": str(s.alias), "name": s.name, "area": s.area.name if s.area else None,
              "balance": _money(s.current_balance), "days": s.days_overdue_base,
              "bucket": next(k for k, lo, hi in BUCKETS if lo <= s.days_overdue_base <= hi)} for s in shops),
            key=lambda r: -r["days"],
        )
        return Response({"summary": aging(shops), "shops": rows})


@extend_schema(responses=OpenApiTypes.OBJECT)
class RepPerformanceView(BusinessScopedMixin, APIView):
    allowed_roles = {Role.OWNER, Role.MANAGER, Role.ACCOUNTANT}

    def get(self, request, business_alias):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        reps = Membership.objects.filter(business=self.business, role=Role.REP, is_active=True).select_related("user")
        data = []
        for m in reps:
            pays = LedgerEntry.objects.filter(
                business=self.business, created_by=m.user, type=EntryType.PAYMENT, reversed_by__isnull=True
            )
            data.append({
                "user_id": m.user_id, "name": m.user.name, "phone": m.user.phone,
                "collected_today": _money(pays.filter(entry_date=today).aggregate(s=Sum("amount"))["s"]),
                "collected_month": _money(pays.filter(entry_date__gte=month_start).aggregate(s=Sum("amount"))["s"]),
                "visits_month": m.user.visits.filter(business=self.business, visited_at__date__gte=month_start).count(),
                "cash_difference_month": _money(sum(
                    (h.difference for h in m.user.handovers.filter(business=self.business, date__gte=month_start)
                     if h.difference is not None), Decimal("0"))),
            })
        return Response(data)
