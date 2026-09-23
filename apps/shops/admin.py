from django.contrib import admin

from .models import Area, Shop, ShopShareLink


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ["name", "business", "area", "current_balance", "credit_limit", "due_since"]
    list_filter = ["business"]
    search_fields = ["name", "owner_name", "phone"]
    readonly_fields = ["current_balance", "last_payment_at", "due_since"]


admin.site.register(Area)
admin.site.register(ShopShareLink)
