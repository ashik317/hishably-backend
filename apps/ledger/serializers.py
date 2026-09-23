from decimal import Decimal

from rest_framework import serializers

from apps.shops.models import Shop

from .models import DIRECTION, EntryType, LedgerEntry, PaymentMethod


class EntrySerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField(source="shop.alias", read_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    signed_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_reversed = serializers.SerializerMethodField()
    reverses = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = LedgerEntry
        fields = [
            "id", "shop", "shop_name", "type", "direction", "amount", "signed_amount", "entry_date",
            "memo_no", "method", "note", "photo", "source", "reverses", "is_reversed",
            "created_by_name", "created_at",
        ]

    def get_is_reversed(self, obj) -> bool:
        return LedgerEntry.objects.filter(reverses=obj).exists() if obj.type != EntryType.REVERSAL else False


class LedgerRowSerializer(EntrySerializer):
    running_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta(EntrySerializer.Meta):
        fields = EntrySerializer.Meta.fields + ["running_balance"]


class EntryCreateSerializer(serializers.Serializer):
    shop = serializers.UUIDField()
    type = serializers.ChoiceField(choices=[c for c in EntryType.values if c in DIRECTION and c != EntryType.OPENING])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    entry_date = serializers.DateField(required=False)
    memo_no = serializers.CharField(required=False, allow_blank=True, max_length=40)
    method = serializers.ChoiceField(choices=PaymentMethod.choices, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    photo = serializers.ImageField(required=False)
    source = serializers.ChoiceField(choices=["manual", "voice", "ocr"], required=False, default="manual")
    approve_over_limit = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs["type"] == EntryType.PAYMENT and not attrs.get("method"):
            raise serializers.ValidationError({"method": "Choose how the payment was made."})
        return attrs

    def validate_shop(self, alias):
        qs = self.context["shop_queryset"]
        try:
            return qs.get(alias=alias)
        except Shop.DoesNotExist:
            raise serializers.ValidationError("Shop not found.")


class ReverseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
