from django.db.models import Count, F
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics

from apps.businesses.models import Role
from apps.common.tenancy import BusinessScopedMixin

from .models import Area, Shop, ShopShareLink
from .serializers import AreaSerializer, ShareLinkSerializer, ShopSerializer

MANAGE = {Role.OWNER, Role.MANAGER}


def shops_for(view):
    """Shops this member may see. Sales reps only see shops in their assigned areas."""
    qs = Shop.objects.filter(business=view.business).select_related("area", "area__assigned_rep")
    if view.is_rep:
        qs = qs.filter(area__assigned_rep=view.request.user)
    return qs


class ShopFilter(filters.FilterSet):
    status = filters.ChoiceFilter(
        choices=[("overdue", "Overdue"), ("over_limit", "Over limit"), ("good", "Good"), ("clear", "Clear")],
        method="filter_status",
    )
    area = filters.NumberFilter(field_name="area_id")
    min_due = filters.NumberFilter(field_name="current_balance", lookup_expr="gte")

    class Meta:
        model = Shop
        fields = ["area", "is_active"]

    def filter_status(self, qs, name, value):
        today = timezone.localdate()
        if value == "over_limit":
            return qs.filter(current_balance__gt=F("credit_limit"))
        if value == "clear":
            return qs.filter(current_balance__lte=0)
        # A shop is overdue when (today - due_since) > due_days.
        ids = [pk for pk, since, days in qs.exclude(due_since=None).values_list("pk", "due_since", "due_days")
               if (today - since).days > days]
        if value == "overdue":
            return qs.filter(pk__in=ids).exclude(current_balance__gt=F("credit_limit"))
        return qs.exclude(pk__in=ids).filter(current_balance__gt=0, current_balance__lte=F("credit_limit"))


class AreaListCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    serializer_class = AreaSerializer
    write_roles = MANAGE
    pagination_class = None

    def get_queryset(self):
        return Area.objects.filter(business=self.business).select_related("assigned_rep").annotate(shop_count=Count("shops"))

    def perform_create(self, serializer):
        serializer.save(business=self.business)


class AreaDetailView(BusinessScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AreaSerializer
    write_roles = MANAGE

    def get_queryset(self):
        return Area.objects.filter(business=self.business).annotate(shop_count=Count("shops"))


class ShopListCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    serializer_class = ShopSerializer
    write_roles = MANAGE
    filterset_class = ShopFilter
    search_fields = ["name", "owner_name", "phone", "area__name"]
    ordering_fields = ["current_balance", "due_since", "name", "created_at"]
    ordering = ["-current_balance"]

    def get_queryset(self):
        return shops_for(self)


class ShopDetailView(BusinessScopedMixin, generics.RetrieveUpdateAPIView):
    serializer_class = ShopSerializer
    write_roles = MANAGE
    lookup_field = "alias"
    lookup_url_kwarg = "shop_alias"

    def get_queryset(self):
        return shops_for(self)


class ShareLinkCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    serializer_class = ShareLinkSerializer
    pagination_class = None

    def get_shop(self):
        return generics.get_object_or_404(shops_for(self), alias=self.kwargs["shop_alias"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ShopShareLink.objects.none()
        return ShopShareLink.objects.filter(shop=self.get_shop(), is_active=True)

    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())
