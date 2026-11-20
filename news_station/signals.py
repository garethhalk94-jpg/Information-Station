"""Signals that run when an article is approved."""

import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Article

logger = logging.getLogger(__name__)

# Where the approved article is logged (this project's own API).
APPROVED_API_URL = getattr(
    settings, "APPROVED_API_URL", "http://127.0.0.1:8000/api/approved/"
)


@receiver(pre_save, sender=Article)
def remember_previous_approval(sender, instance, **kwargs):
    """Record whether the article was already approved before this save."""
    instance._was_approved = (
        instance.pk is not None
        and Article.objects.filter(pk=instance.pk, approved=True).exists()
    )


@receiver(post_save, sender=Article)
def handle_article_approved(sender, instance, raw=False, **kwargs):
    """Notify subscribers only when approved changes from False to True."""
    if raw:  # loading fixtures: do nothing
        return
    if instance.approved and not getattr(instance, "_was_approved", False):
        email_subscribers(instance)
        log_to_approved_api(instance)


def get_subscriber_emails(article):
    """Emails of readers subscribed to the author or the publisher."""
    query = Q(subscribed_journalists=article.author)
    # Only add the publisher test when there is one: filtering on None
    # would match readers with no publisher subscriptions at all.
    if article.publisher_id:
        query |= Q(subscribed_publishers=article.publisher)

    return list(
        get_user_model()
        .objects.filter(query)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )


def email_subscribers(article):
    """Email the approved article to its subscribers (BCC, one message)."""
    recipients = get_subscriber_emails(article)
    if not recipients:
        return

    source = article.publisher.name if article.publisher else "Independent"
    body = (
        f"{article.title}\n"
        f"By {article.author.username} ({source})\n\n"
        f"{article.content}\n"
    )
    message = EmailMessage(
        subject=f"New article: {article.title}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        bcc=recipients,
    )
    try:
        message.send()
    except OSError:
        # A mail problem must never undo the approval.
        logger.exception(
            "Could not email subscribers for article %s", article.pk
        )


def log_to_approved_api(article):
    """POST the approved article to this project's /api/approved/ endpoint."""
    payload = {
        "id": article.pk,
        "title": article.title,
        "content": article.content,
        "author": article.author.username,
        "publisher": article.publisher.name if article.publisher else None,
    }
    try:
        response = requests.post(APPROVED_API_URL, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Could not log article %s to the API", article.pk)
