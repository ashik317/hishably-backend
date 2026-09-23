from django.contrib import admin

from .models import ReminderRule, SmsMessage, SmsTemplate


@admin.register(SmsMessage)
class SmsMessageAdmin(admin.ModelAdmin):
    list_display = ["created_at", "business", "shop", "phone", "kind", "status", "parts"]
    list_filter = ["status", "kind"]


admin.site.register(SmsTemplate)
admin.site.register(ReminderRule)
