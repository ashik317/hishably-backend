from django.contrib import admin

from .models import Business, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ["name", "trade_type", "plan", "owner", "created_at"]
    search_fields = ["name", "owner__phone"]
    inlines = [MembershipInline]
