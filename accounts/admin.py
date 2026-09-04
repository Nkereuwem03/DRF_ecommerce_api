from django.contrib import admin

from .models import Token, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "account_status",
        "is_email_verified",
        "is_active",
        "is_staff",
        "date_joined",
    ]

    list_filter = [
        "account_status",
        "is_email_verified",
        "is_active",
        "is_staff",
    ]

    search_fields = [
        "email",
    ]

    readonly_fields = [
        "id",
        "date_joined",
        "updated_at",
        "email_verified_at",
    ]


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "purpose",
        "status",
        "created_at",
        "expires_at",
        "verified_at",
    ]

    list_filter = [
        "purpose",
        "status",
    ]

    search_fields = [
        "user__email",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "verified_at",
    ]
