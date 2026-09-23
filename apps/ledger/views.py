from decimal import Decimal

from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.businesses.models import Role
from apps.common.tenancy import BusinessScopedMixin
from apps.shops.models import ShopShareLink
from apps.shops.views import shops_for

from .models import LedgerEntry
from .serializers import EntryCreateSerializer, EntrySerializer, LedgerRowSerializer, ReverseSerializer
from .services import post_entry, reverse_entry

WRITERS = {Role.OWNER, Role.MANAGER, Role.REP}  # accountants are read-only


class EntryFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="entry_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="entry_date", lookup_expr="lte")
    shop = filters.UUIDFilter(field_name="shop__alias")
    area = filters.NumberFilter(field_name="shop__area_id")

    class Meta:
        model = LedgerEntry
        fields = ["type", "method", "created_by", "source"]


class EntryListCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    """GET: all entries with filters. POST: record a sale, payment, return or discount.

    Send an `Idempotency-Key` header so a retried request never posts twice.
    """

    write_roles = WRITERS
    filterset_class = EntryFilter
    search_fields = ["memo_no", "note", "shop__name"]
    ordering = ["-entry_date", "-id"]

    def get_queryset(self):
        return (
            LedgerEntry.objects.filter(business=self.business, shop__in=shops_for(self))
            .select_related("shop", "created_by")
        )

    def get_serializer_class(self):
        return EntryCreateSerializer if self.request.method == "POST" else EntrySerializer

    def create(self, request, *args, **kwargs):
        s = EntryCreateSerializer(data=request.data, context={"shop_queryset": shops_for(self)})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        can_approve = self.membership.role in (Role.OWNER, Role.MANAGER)
        entry = post_entry(
            shop=d["shop"], entry_type=d["type"], amount=d["amount"], user=request.user,
            entry_date=d.get("entry_date"), memo_no=d.get("memo_no", ""), method=d.get("method", ""),
            note=d.get("note", ""), source=d.get("source", "manual"), photo=d.get("photo"),
            idempotency_key=request.headers.get("Idempotency-Key"),
            allow_over_limit=d["approve_over_limit"] and can_approve,
        )
        entry.shop.refresh_from_db()
        data = EntrySerializer(entry).data
        data["shop_balance"] = str(entry.shop.current_balance)
        return Response(data, status=status.HTTP_201_CREATED)


class ShopLedgerView(BusinessScopedMixin, generics.ListAPIView):
    """A shop's ledger, newest first, with the running balance after each entry."""

    serializer_class = LedgerRowSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LedgerEntry.objects.none()
        self.shop = get_object_or_404(shops_for(self), alias=self.kwargs["shop_alias"])
        rows = list(self.shop.entries.select_related("shop", "created_by").order_by("entry_date", "id"))
        running = Decimal("0")
        for e in rows:
            running += e.signed_amount
            e.running_balance = running
        return rows[::-1]


class ReverseEntryView(BusinessScopedMixin, APIView):
    serializer_class = ReverseSerializer
    allowed_roles = {Role.OWNER, Role.MANAGER}

    def post(self, request, business_alias, pk):
        entry = get_object_or_404(LedgerEntry, business=self.business, pk=pk)
        s = ReverseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        reversal = reverse_entry(entry=entry, user=request.user, reason=s.validated_data["reason"])
        return Response(EntrySerializer(reversal).data, status=status.HTTP_201_CREATED)


@extend_schema(responses=OpenApiTypes.OBJECT)
class PublicLedgerView(APIView):
    """What a shop sees from its SMS link. No login; the token is the credential."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def get(self, request, token):
        link = get_object_or_404(ShopShareLink.objects.select_related("shop__business"), token=token)
        if not link.is_valid:
            return Response({"detail": "This link has expired."}, status=status.HTTP_410_GONE)
        shop = link.shop
        recent = shop.entries.order_by("-entry_date", "-id")[:20]
        return Response({
            "business": {"name": shop.business.name, "address": shop.business.address, "phone": shop.business.phone},
            "shop": {"name": shop.name, "owner_name": shop.owner_name},
            "current_balance": str(shop.current_balance),
            "credit_limit": str(shop.credit_limit),
            "allow_payment": link.allow_payment,
            "entries": [
                {"date": e.entry_date, "type": e.type, "memo_no": e.memo_no, "amount": str(e.signed_amount)}
                for e in recent
            ],
        })
