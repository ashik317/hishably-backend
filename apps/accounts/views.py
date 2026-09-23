from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.providers import get_sms_provider

from .models import OTPCode, User
from .serializers import PhoneSerializer, UserSerializer, VerifySerializer


class SendOTPView(APIView):
    serializer_class = PhoneSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        s = PhoneSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone"]
        code = OTPCode.issue(phone)
        get_sms_provider().send(phone, f"Hishably code: {code}. It expires in {settings.OTP_TTL_MINUTES} minutes.")
        data = {"detail": "Code sent.", "phone": phone}
        if settings.OTP_DEBUG:
            data["debug_code"] = code  # never enable in production
        return Response(data)


class VerifyOTPView(APIView):
    serializer_class = VerifySerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        s = VerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone"]
        if not OTPCode.verify(phone, s.validated_data["code"]):
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        user, created = User.objects.get_or_create(phone=phone)
        if s.validated_data.get("name") and not user.name:
            user.name = s.validated_data["name"]
            user.save(update_fields=["name"])
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh), "user": UserSerializer(user).data, "is_new": created}
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
