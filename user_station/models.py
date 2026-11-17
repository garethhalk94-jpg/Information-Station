"""Models for the user_station app: the custom user and its role logic."""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction

from .roles import get_role_group


class CustomUser(AbstractUser):
    """A user with a single role that determines their group and fields."""

    class Role(models.TextChoices):
        READER = "reader", "Reader"
        EDITOR = "editor", "Editor"
        JOURNALIST = "journalist", "Journalist"

    # Maps each role to the name of the group it belongs to.
    ROLE_GROUP_NAMES = {
        Role.READER: "Readers",
        Role.EDITOR: "Editors",
        Role.JOURNALIST: "Journalists",
    }

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.READER,
    )

    # Reader-only fields: who the reader follows.
    subscribed_publishers = models.ManyToManyField(
        "news_station.Publisher",
        blank=True,
        related_name="subscribers",
    )
    subscribed_journalists = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="subscribers",
        limit_choices_to={"role": "journalist"},
    )

    # Journalist content is available through reverse relations:
    #   user.articles     (Article.author, related_name="articles")
    #   user.newsletters  (Newsletter.author, related_name="newsletters")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_reader(self):
        return self.role == self.Role.READER

    @property
    def is_editor(self):
        return self.role == self.Role.EDITOR

    @property
    def is_journalist(self):
        return self.role == self.Role.JOURNALIST

    def save(self, *args, **kwargs):
        """Save the user, then sync their group and role-specific fields."""
        with transaction.atomic():
            super().save(*args, **kwargs)  # pk must exist before touching M2M
            self._sync_group()
            self._clear_irrelevant_fields()

    # Just double check this. There is a refresh  of the group's permissions
    def _sync_group(self):
        """Put the user in exactly one group, based on their role."""
        group = get_role_group(self.ROLE_GROUP_NAMES[self.role])
        self.groups.set([group])

    def _clear_irrelevant_fields(self):
        """Journalists have no subscriptions; non-journalists own no content.

        The brief says to set the other role's fields to None. M2M fields
        cannot hold None, so they are emptied instead.
        """
        if not self.is_reader:
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()


class ResetToken(models.Model):
    """A single-use password reset token. Only the hash is stored."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reset_tokens",
    )
    token = models.CharField(max_length=64, db_index=True)  # sha256 hash
    expiry_date = models.DateTimeField()
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"Reset token for {self.user} (used: {self.used})"
