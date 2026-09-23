from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import Role
from apps.common.tenancy import BusinessScopedMixin
from apps.ledger.models import EntryType, LedgerEntry
from apps.ledger.services import post_entry
from apps.shops.serializers import ShopSerializer
from apps.shops.views import shops_for

from .models import CashHandover, CollectionVisit
from .serializers import HandoverSerializer, VisitSerializer


def expected_cash(business, rep, date):
    return (
        LedgerEntry.objects.filter(
            business=business, created_by=rep, type=EntryType.PAYMENT, method="cash",
            entry_date=date, reversed_by__isnull=True,
        ).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    )


class MyRouteView(BusinessScopedMixin, generics.ListAPIView):
    """Today's route for the logged-in rep: shops in my areas with a balance, oldest due first."""

    serializer_class = ShopSerializer
    pagination_class = None

    def get_queryset(self):
        qs = shops_for(self).filter(current_balance__gt=0)
        if not self.is_rep:
            qs = qs.filter(area__assigned_rep=self.request.user)
        return qs.order_by("due_since")


class VisitListCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    serializer_class = VisitSerializer
    write_roles = {Role.OWNER, Role.MANAGER, Role.REP}

    def get_queryset(self):
        qs = CollectionVisit.objects.filter(business=self.business).select_related("shop", "rep", "payment")
        return qs.filter(rep=self.request.user) if self.is_rep else qs

    def perform_create(self, serializer):
        d = serializer.validated_data
        shop = get_object_or_404(shops_for(self), alias=d.pop("shop"))
        amount, method = d.pop("amount", None), d.pop("method", "cash")
        payment = None
        if amount:
            payment = post_entry(shop=shop, entry_type=EntryType.PAYMENT, amount=amount, user=self.request.user,
                                 method=method, note="Collected on visit")
        serializer.save(business=self.business, rep=self.request.user, shop=shop, payment=payment,
                        visited_at=timezone.now())


class HandoverListCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    """Reps submit today's handover; the expected amount is calculated from their cash payments."""

    serializer_class = HandoverSerializer
    write_roles = {Role.REP, Role.MANAGER, Role.OWNER}

    def get_queryset(self):
        qs = CashHandover.objects.filter(business=self.business).select_related("rep")
        return qs.filter(rep=self.request.user) if self.is_rep else qs

    def create(self, request, *args, **kwargs):
        today = timezone.localdate()
        handover, _ = CashHandover.objects.get_or_create(
            business=self.business, rep=request.user, date=today,
            defaults={"expected_amount": expected_cash(self.business, request.user, today)},
        )
        if handover.status == CashHandover.Status.PENDING:
            handover.expected_amount = expected_cash(self.business, request.user, today)
            handover.note = request.data.get("note", handover.note)
            handover.save(update_fields=["expected_amount", "note", "updated_at"])
        return Response(HandoverSerializer(handover).data, status=status.HTTP_201_CREATED)


@extend_schema(request=OpenApiTypes.OBJECT, responses=HandoverSerializer)
class ConfirmHandoverView(BusinessScopedMixin, APIView):
    allowed_roles = {Role.OWNER, Role.MANAGER}

    def post(self, request, business_alias, pk):
        h = get_object_or_404(CashHandover, business=self.business, pk=pk)
        try:
            handed = Decimal(str(request.data["handed_amount"]))
        except (KeyError, ArithmeticError, ValueError):
            return Response({"handed_amount": "Enter the cash you received."}, status=400)
        h.handed_amount = handed
        h.status = CashHandover.Status.CONFIRMED if handed == h.expected_amount else CashHandover.Status.DIFFERENCE
        h.confirmed_by = request.user
        h.save()
        return Response(HandoverSerializer(h).data)
