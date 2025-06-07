from datetime import datetime, timezone

from django.contrib import auth, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.crypto import get_random_string

from common.tasks import send_email

from .decorators import redirect_autheticated_user
from .models import PendingUser, Token, TokenType, User

# Create your views here.


def home(request: HttpRequest):
    return render(request, "home.html")


@redirect_autheticated_user
def login(request: HttpRequest):
    if request.method == "POST":
        email: str = request.POST.get("email")
        password: str = request.POST.get("password")

        user = auth.authenticate(request, email=email, password=password)

        if user is not None:
            auth.login(request, user)
            messages.success(request, "You are now logged in")
            return redirect("home")
        else:
            messages.error(request, "Invalid credentials")
            return redirect("login")

    else:
        return render(request, "login.html")


def logout(request: HttpRequest):
    auth.logout(request)
    messages.success(request, "You are now logged out.")
    return redirect("home")


@redirect_autheticated_user
def register(request):
    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')

        # Basic validation
        if not email or not password or not confirm_password or not role:
            messages.error(request, "Please fill in all required fields.")
            return redirect('register')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(email=email).exists() or PendingUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered or pending verification.")
            return redirect('register')

        verification_code = get_random_string(6, allowed_chars='0123456789')
        hashed_password = make_password(password)

        pending_user = PendingUser.objects.create(
            email=email,
            password=hashed_password,
            role=role,
            verification_code=verification_code,
            created_at=datetime.now(timezone.utc)
        )

        email_data = {
            "email": email,
            "verification_code": verification_code,
            "role": role,
        }

        send_email.delay(
            "Verify your email",
            [email],
            "emails/email_verification_template.html",
            email_data,
        )

        messages.success(request, "Registration successful. Please check your email to verify your account.")
        return redirect('verify_account')

    return render(request, 'register.html')


def verify_account(request):
    if request.method == "POST":
        verification_code = request.POST.get("verification_code", "")
        email = request.POST.get("email", "").lower()

        pending_user = PendingUser.objects.filter(verification_code=verification_code, email=email).first()

        if pending_user and pending_user.is_valid():
            with transaction.atomic():
                user = User.objects.create(
                    email=pending_user.email,
                    password=pending_user.password,
                    role=pending_user.role
                )
                pending_user.delete()

            auth.login(request, user)
            messages.success(request, "Account verified. You are now logged in.")
            return redirect("home")
        else:
            messages.error(request, "Invalid or expired verification code.")
            return render(request, "verify_account.html", {"email": email}, status=400)

    email = request.GET.get("email", "")
    return render(request, "verify_account.html", {"email": email})




def send_password_reset_link(request: HttpRequest):
    if request.method == "POST":
        email: str = request.POST.get("email", "")
        user = get_user_model().objects.filter(email=email.lower()).first()

        if user:
            token, _ = Token.objects.update_or_create(
                user=user,
                token_type=TokenType.PASSWORD_RESET,
                defaults={
                    "token": get_random_string(20),
                    "created_at": datetime.now(timezone.utc),
                },
            )

            email_data = {"email": email.lower(), "token": token.token}
            send_email.delay(
                "Your Password Reset Link",
                [email],
                "emails/password_reset_template.html",
                email_data,
            )
            messages.success(request, "Reset link sent to your email")
            return redirect("reset_password_via_email")

        else:
            messages.error(request, "Email not found")
            return redirect("reset_password_via_email")

    else:
        return render(request, "forgot_password.html")


def verify_password_reset_link(request: HttpRequest):
    email = request.GET.get("email")
    reset_token = request.GET.get("token")

    token: Token = Token.objects.filter(
        user__email=email, token=reset_token, token_type=TokenType.PASSWORD_RESET
    ).first()

    if not token or not token.is_valid():
        messages.error(request, "Invalid or expired reset link.")
        return redirect("reset_password_via_email")

    return render(
        request,
        "set_new_password_using_reset_token.html",
        context={"email": email, "token": reset_token},
    )


def set_new_password_using_reset_link(request: HttpRequest):
    """Set a new password given the token sent to the user email"""

    if request.method == "POST":
        password1: str = request.POST.get("password1")
        password2: str = request.POST.get("password2")
        email: str = request.POST.get("email")
        reset_token = request.POST.get("token")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return render(
                request,
                "set_new_password_using_reset_token.html",
                {"email": email, "token": reset_token},
            )

        token: Token = Token.objects.filter(
            token=reset_token, token_type=TokenType.PASSWORD_RESET, user__email=email
        ).first()

        if not token or not token.is_valid():
            messages.error(request, "Expired or Invalid reset link")
            return redirect("reset_password_via_email")

        token.reset_user_password(password1)
        token.delete()
        messages.success(request, "Password changed.")
        return redirect("login")
