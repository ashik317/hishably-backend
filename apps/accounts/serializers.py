import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from rest_framework import serializers
from apps.common.phone import normalize_bd_phone
from .models import User, EmailVerification


class AccountRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "alias",
            "email",
            "phone",
            "title",
            "first_name",
            "middle_name",
            "last_name",
            "current_address",
            "ni_number",
            "profile_image",
            "password",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        code = str(random.randint(100000, 999999))

        EmailVerification.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        send_mail(
            subject="Verify your email",
            message=f"Your verification code is: {code}",
            from_email=None,
            recipient_list=[user.email],
        )

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance



class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email.")

        try:
            verification = user.email_verification
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("No verification code found.")

        if verification.is_verified:
            raise serializers.ValidationError("Email already verified.")

        if verification.is_expired():
            raise serializers.ValidationError(
                "Code has expired. Please request a new one."
            )

        if verification.code != data["code"]:
            raise serializers.ValidationError("Invalid code.")

        data["user"] = user
        data["verification"] = verification
        return data

    def save(self):
        user = self.validated_data["user"]
        verification = self.validated_data["verification"]
        verification.is_verified = True
        verification.save()
        user.is_active = True
        user.save()
        return user


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
