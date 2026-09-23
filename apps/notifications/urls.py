from django.urls import path

from .views import ReminderRuleView, RemindShopView, SmsLogView, TemplateListView

urlpatterns = [
    path("shops/<uuid:shop_alias>/remind/", RemindShopView.as_view(), name="shop-remind"),
    path("sms/", SmsLogView.as_view(), name="sms-log"),
    path("sms/templates/", TemplateListView.as_view(), name="sms-templates"),
    path("reminder-rules/", ReminderRuleView.as_view(), name="reminder-rules"),
]
