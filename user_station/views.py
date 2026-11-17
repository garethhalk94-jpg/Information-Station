"""
user_station/views.py
Views for user_station: registration, login, logout and reset.
"""

import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import CustomUser
from .password_reset import (
    build_reset_email,
    create_reset_token,
    get_valid_token,
)

logger = logging.getLogger(__name__)

# How long a login session lasts
SESSION_TIMEOUT = 60 * 60

# Role a visitor may pick when registering.
# To stop people registering themselves as Editors,
# use:
# [CustomUser.Role.READER, CustomUser.Role.JOURNALIST]
REGISTRATION_ROLES = [
    CustomUser.Role.READER,
    CustomUser.Role.JOURNALIST,
]


def validate_registration(username, email, password, password_confirm, role):
    """
    Check the registration details and return a list of error messages.

    An empty list means every detail is valid
    """

    errors = []

    # Username validation
    if not username:
        errors.append("Please enter a username.")
    elif CustomUser.objects.filter(username__iexact=username).exists():
        errors.append("Username is already in use.")

    # Email validation
    try:
        validate_email(email)
    except ValidationError:
        errors.append("Please enter a valid email address.")
    else:
        if CustomUser.objects.filter(email__iexact=email).exists():
            errors.append("Email is already in use.")

    # Password validation
    try:
        validate_password(password)
    except ValidationError as error:
        errors.extend(error.messages)
    if password != password_confirm:
        errors.append("Passwords do not match.")

    # Role validation
    # Editors can only be added by admin
    if role == CustomUser.Role.EDITOR:
        errors.append("Editors can only be added by an administrator")
    elif role not in REGISTRATION_ROLES:
        errors.append("Please choose an account type.")

    return errors


def render_registration_errors(request, errors, username, email, role):
    """
    Show the registration form again with errors and the entered data
    """

    return render(
        request,
        "user_station/register.html",
        {
            "errors": errors,
            "form_data": {
                "username": username,
                "email": email,
                "account_type": role,
            },
        },
    )


def register(request):
    """
    Register a new Reader, Journalist, Editor account.
    On GET, show the registration form. On POST, validate the details,
    create the CustomUser with the chosen role and adds them to the
    according Group, then log them in and redirect to the home page.
    """

    if request.method != "POST":
        return render(request, "user_station/register.html")

    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    role = request.POST.get("account_type")

    errors = validate_registration(
        username, email, password, password_confirm, role
    )

    if errors:
        return render_registration_errors(
            request, errors, username, email, role
        )

    try:
        with transaction.atomic():
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=email,
                role=role,
            )
    except IntegrityError:
        # Someone else took the username between the check and the save.
        return render_registration_errors(
            request, ["Username is already in use."], username, email, role
        )

    login(request, user)
    request.session.set_expiry(SESSION_TIMEOUT)
    return redirect("home")


def login_user(request):
    """
    Log a user in with a username and password.

    On GET, show the form. On POST, authenticate the credentials and
    redirect to the home page, or show a generic error message.
    """

    if request.method != "POST":
        return render(request, "user_station/login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    user = authenticate(request, username=username, password=password)
    if user is None:
        return render(
            request,
            "user_station/login.html",
            {
                "error": "Invalid username or password",
                "form_data": {"username": username},
            },
        )

    login(request, user)
    request.session.set_expiry(SESSION_TIMEOUT)
    return redirect("home")


@require_POST
def logout_user(request):
    """
    Log the current user out (POST only) and show the login page.
    """

    logout(request)
    return redirect("login")


def forgot_password(request):
    """
    Email a reset link to the account that owns an email address.

    The response is the same whether or not the email is registered,
    so it cannot be used to discover which emails have accounts.
    """

    if request.method != "POST":
        return render(request, "user_station/forgot_password.html")

    email = request.POST.get("email", "").strip()

    user = None
    if email:
        user = CustomUser.objects.filter(email__iexact=email).first()

    if user is not None:
        raw_token = create_reset_token(user)
        reset_url = request.build_absolute_uri(
            reverse("reset_password", args=[raw_token])
        )
        try:
            build_reset_email(user, reset_url).send()
        except OSError:
            # Stay silent to the visitor: an error would reveal that the
            # email exists. Record it for the developer instead.
            logger.exception("Could not send reset email to user %s", user.pk)

    # Same message whether or not the email exists.
    messages.success(
        request,
        "If that email is registered, a reset link has been sent.",
    )
    return redirect("login")


def reset_password(request, token):
    """
    Let a user choose a new password using a reset link token.

    The token must exist, be unused and be unexpired. It is marked as
    used once the password has been changed.
    """

    reset_token = get_valid_token(token)
    if reset_token is None:
        messages.error(
            request,
            "That reset link is invalid or has expired. "
            "Please request a new one.",
        )
        return redirect("forgot_password")

    if request.method != "POST":
        return render(request, "user_station/reset_password.html")

    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")

    errors = []
    try:
        validate_password(password, reset_token.user)
    except ValidationError as error:
        errors.extend(error.messages)

    if password != password_confirm:
        errors.append("Passwords do not match.")

    if errors:
        return render(
            request,
            "user_station/reset_password.html",
            {"errors": errors},
        )

    with transaction.atomic():
        user = reset_token.user
        user.set_password(password)
        user.save()
        reset_token.used = True
        reset_token.save()

    messages.success(request, "Your password has been changed. Please log in.")
    return redirect("login")
