from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.phone import normalize_bd_phone

from .models import Business, Membership, Role


class BusinessSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "alias", "name", "trade_type", "phone", "address", "trade_licence", "logo",
            "default_credit_limit", "default_due_days", "require_owner_approval_over_limit",
            "plan", "my_role", "created_at",
        ]
        read_only_fields = ["alias", "plan", "created_at"]

    def get_my_role(self, obj) -> str | None:
        user = self.context["request"].user
        m = next((m for m in obj.memberships.all() if m.user_id == user.id), None)
        return m.role if m else None

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        business = Business.objects.create(owner=user, **validated_data)
        Membership.objects.create(business=business, user=user, role=Role.OWNER)
        return business


class MemberSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="user.phone", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "phone", "name", "role", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class InviteSerializer(serializers.Serializer):
    phone = serializers.CharField()
    name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=[Role.MANAGER, Role.REP, Role.ACCOUNTANT])

    def validate_phone(self, value):
        return normalize_bd_phone(value)

    def create(self, validated_data):
        business = self.context["business"]
        user, _ = User.objects.get_or_create(phone=validated_data["phone"], defaults={"name": validated_data["name"]})
        membership, created = Membership.objects.get_or_create(
            business=business, user=user,
            defaults={"role": validated_data["role"], "invited_by": self.context["request"].user},
        )
        if not created:
            raise serializers.ValidationError({"phone": "This person is already a member."})
        return membership
