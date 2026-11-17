"""Admin configuration for user_station."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.action(description="Make selected users editors")
def make_editors(modeladmin, request, queryset):
    for user in queryset:
        user.role = CustomUser.Role.EDITOR
        user.save()  # fixes the group and clears reader fields
    modeladmin.message_user(
        request, f"{queryset.count()} user(s) are now editors."
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Show the role and subscriptions on the user pages."""

    list_display = ("username", "email", "role", "is_staff")
    list_filter = ("role", "is_staff")
    actions = [make_editors]
    filter_horizontal = UserAdmin.filter_horizontal + (
        "subscribed_publishers",
        "subscribed_journalists",
    )
    fieldsets = UserAdmin.fieldsets + (
        (
            "Role and subscriptions",
            {
                "fields": (
                    "role",
                    "subscribed_publishers",
                    "subscribed_journalists",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "role")}),
    )
