from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from apps.common.phone import normalize_bd_phone

from .models import Area, Shop, ShopShareLink


class AreaSerializer(serializers.ModelSerializer):
    shop_count = serializers.IntegerField(read_only=True)
    assigned_rep_name = serializers.CharField(source="assigned_rep.name", read_only=True, default=None)

    class Meta:
        model = Area
        fields = ["id", "name", "assigned_rep", "assigned_rep_name", "sort_order", "shop_count"]

    def validate_assigned_rep(self, user):
        if user and not user.memberships.filter(business=self.context["business"], is_active=True).exists():
            raise serializers.ValidationError("This person is not a member of your business.")
        return user


class ShopSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True, default=None)
    rep_name = serializers.CharField(source="area.assigned_rep.name", read_only=True, default=None)
    status = serializers.CharField(read_only=True)
    days_overdue = serializers.IntegerField(source="days_overdue_base", read_only=True)
    limit_used_pct = serializers.SerializerMethodField()
    opening_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, write_only=True, required=False, min_value=Decimal("0")
    )

    class Meta:
        model = Shop
        fields = [
            "alias", "name", "owner_name", "phone", "address", "notes", "photo",
            "area", "area_name", "rep_name", "credit_limit", "due_days", "is_active",
            "current_balance", "last_payment_at", "due_since", "days_overdue", "status",
            "limit_used_pct", "opening_balance", "created_at",
        ]
        read_only_fields = ["alias", "current_balance", "last_payment_at", "due_since", "created_at"]

    def get_limit_used_pct(self, obj) -> float | None:
        return round(float(obj.current_balance / obj.credit_limit * 100), 1) if obj.credit_limit else None

    def validate_phone(self, value):
        return normalize_bd_phone(value) if value else value

    def validate_area(self, area):
        if area and area.business_id != self.context["business"].id:
            raise serializers.ValidationError("Unknown area.")
        return area

    def create(self, validated_data):
        from apps.ledger.models import EntryType
        from apps.ledger.services import post_entry

        opening = validated_data.pop("opening_balance", None)
        business = self.context["business"]
        validated_data.setdefault("credit_limit", business.default_credit_limit)
        validated_data.setdefault("due_days", business.default_due_days)
        shop = Shop.objects.create(business=business, **validated_data)
        if opening:
            post_entry(
                shop=shop, entry_type=EntryType.OPENING, amount=opening,
                user=self.context["request"].user, note="Opening balance", allow_over_limit=True,
            )
            shop.refresh_from_db()
        return shop

    def update(self, instance, validated_data):
        validated_data.pop("opening_balance", None)
        return super().update(instance, validated_data)


class ShareLinkSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ShopShareLink
        fields = ["token", "url", "expires_at", "allow_payment", "is_active", "created_at"]
        read_only_fields = ["token", "url", "is_active", "created_at"]

    def get_url(self, obj) -> str:
        return f"{settings.PUBLIC_BASE_URL}/p/{obj.token}"
