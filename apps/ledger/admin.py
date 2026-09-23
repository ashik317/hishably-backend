from django.contrib import admin

from .models import AuditLog, LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "shop", "type", "amount", "entry_date", "created_by"]
    list_filter = ["type", "business"]
    search_fields = ["shop__name", "memo_no"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "business", "user", "action", "object_id"]
    list_filter = ["action"]
