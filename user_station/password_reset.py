import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import ResetToken

"""
Helpers for the password reset flow (token handling and email).
"""

# How long a reset link stays valid.
RESET_TOKEN_MINUTES = 15


def hash_token(raw_token):
    """
    Return the SHA-256 hash of a raw reset token, for safe storage.
    """

    return hashlib.sha256(raw_token.encode()).hexdigest()


def get_valid_token(raw_token):
    """
    Return the matching unused, unexpired ResetToken, or None.
    """

    return (
        ResetToken.objects.select_related("user")
        .filter(
            token=hash_token(raw_token),
            used=False,
            expiry_date__gt=timezone.now(),
        )
        .first()
    )


def create_reset_token(user):
    """
    Create a reset token for a user and return the raw token.

    Older unused tokens are invalidated so only the newest link works.
    Only the hash is stored; the raw token goes into the email link.
    """

    ResetToken.objects.filter(user=user, used=False).update(used=True)

    raw_token = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(minutes=RESET_TOKEN_MINUTES)
    ResetToken.objects.create(
        user=user,
        token=hash_token(raw_token),
        expiry_date=expires,
    )
    return raw_token


def build_reset_email(user, reset_url):
    """
    Build the password reset email containing the reset link.
    """

    body = (
        f"Hi {user.username},\n\n"
        f"Here is your link to reset your password:\n{reset_url}\n\n"
        f"It expires in {RESET_TOKEN_MINUTES} minutes. If you didn't "
        f"request this, you can ignore this email.\n"
    )
    return EmailMessage(
        subject="Information Station password reset",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
