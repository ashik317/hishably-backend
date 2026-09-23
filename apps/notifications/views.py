from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import Role
from apps.common.tenancy import BusinessScopedMixin
from apps.shops.views import shops_for

from .models import DEFAULT_TEMPLATES, ReminderRule, SmsMessage, SmsTemplate
from .serializers import ReminderRuleSerializer, RemindSerializer, SmsMessageSerializer, TemplateSerializer
from .services import queue_sms

MANAGE = {Role.OWNER, Role.MANAGER}


class RemindShopView(BusinessScopedMixin, APIView):
    serializer_class = RemindSerializer
    allowed_roles = {Role.OWNER, Role.MANAGER, Role.REP}

    def post(self, request, business_alias, shop_alias):
        shop = get_object_or_404(shops_for(self), alias=shop_alias)
        if not shop.phone:
            return Response({"detail": "This shop has no phone number."}, status=400)
        s = RemindSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        msg = queue_sms(shop, s.validated_data["kind"], s.validated_data.get("body"))
        msg.refresh_from_db()
        return Response(SmsMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class SmsLogView(BusinessScopedMixin, generics.ListAPIView):
    serializer_class = SmsMessageSerializer
    allowed_roles = MANAGE | {Role.ACCOUNTANT}
    filterset_fields = ["status", "kind"]

    def get_queryset(self):
        return SmsMessage.objects.filter(business=self.business).select_related("shop")


class TemplateListView(BusinessScopedMixin, APIView):
    serializer_class = TemplateSerializer
    allowed_roles = MANAGE

    def get(self, request, business_alias):
        saved = {t.kind: t.body for t in SmsTemplate.objects.filter(business=self.business)}
        return Response([{"kind": k, "body": saved.get(k, v)} for k, v in DEFAULT_TEMPLATES.items()])

    def put(self, request, business_alias):
        s = TemplateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        SmsTemplate.objects.update_or_create(business=self.business, kind=s.validated_data["kind"],
                                             defaults={"body": s.validated_data["body"]})
        return Response(s.data)


class ReminderRuleView(BusinessScopedMixin, generics.RetrieveUpdateAPIView):
    serializer_class = ReminderRuleSerializer
    allowed_roles = MANAGE

    def get_object(self):
        return ReminderRule.objects.get_or_create(business=self.business)[0]
