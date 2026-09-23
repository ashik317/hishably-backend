from django.contrib import admin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["phone", "name", "language", "is_active", "date_joined"]
    search_fields = ["phone", "name"]


@admin.register(OTPCode)
class OTPAdmin(admin.ModelAdmin):
    list_display = ["phone", "expires_at", "attempts", "used"]
