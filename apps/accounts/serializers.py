from rest_framework import serializers

from apps.common.phone import normalize_bd_phone

from .models import User


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        return normalize_bd_phone(value)


class VerifySerializer(PhoneSerializer):
    code = serializers.RegexField(r"^\d{6}$")
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "name", "language", "date_joined"]
        read_only_fields = ["id", "phone", "date_joined"]
