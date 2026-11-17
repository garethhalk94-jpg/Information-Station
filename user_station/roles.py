"""
Roles and their permissions.
Roles are either Reader, Journalist or Editor,
with Readers only having 2 permissions,
Journalists having 8 permissions,
and Editors having 6 permissions.
"""

from django.contrib.auth.models import Group, Permission
from django.db import transaction

ROLE_PERMISSIONS = {
    "Readers": [
        "view_article",
        "view_newsletter",
    ],
    "Journalists": [
        "view_article",
        "add_article",
        "change_article",
        "delete_article",
        "view_newsletter",
        "add_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ],
    "Editors": [
        "view_article",
        "change_article",
        "delete_article",
        "view_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ],
}


def apply_role_permissions(group):
    """
    Give a group the permissions defined for its role.

    Returns how many permissions the group now has.
    """

    permissions = Permission.objects.filter(
        content_type__app_label="news_station",
        codename__in=ROLE_PERMISSIONS[group.name],
    )
    group.permissions.set(permissions)
    return permissions.count()


def get_role_group(name):
    """
    Return the group for a role, creating and equipping it if missing.
    """

    if name not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: {name}")

    with transaction.atomic():
        group, created = Group.objects.get_or_create(name=name)
        if created or not group.permissions.exists():
            apply_role_permissions(
                group
            )  # Only need this? if created... can go?
    return group
