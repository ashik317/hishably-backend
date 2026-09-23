from rest_framework import serializers

from .models import CashHandover, CollectionVisit


class VisitSerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField(write_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    rep_name = serializers.CharField(source="rep.name", read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, min_value=0)
    method = serializers.CharField(write_only=True, required=False, default="cash")
    collected_amount = serializers.DecimalField(source="payment.amount", max_digits=12, decimal_places=2, read_only=True, default=None)

    class Meta:
        model = CollectionVisit
        fields = ["id", "shop", "shop_name", "rep_name", "visited_at", "lat", "lng", "note", "amount", "method", "collected_amount"]
        read_only_fields = ["id", "visited_at"]


class HandoverSerializer(serializers.ModelSerializer):
    rep_name = serializers.CharField(source="rep.name", read_only=True)
    difference = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CashHandover
        fields = ["id", "rep", "rep_name", "date", "expected_amount", "handed_amount", "difference", "status", "note"]
        read_only_fields = ["id", "rep", "expected_amount", "status"]
