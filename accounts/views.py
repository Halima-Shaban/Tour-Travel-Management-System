from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from messaging.services import threads_for
from tours import services
from tours.forms import ParticipantFormSet

from .forms import (
    ForgotPasswordForm,
    LoginForm,
    ProfileForm,
    ResetPasswordForm,
    SignUpForm,
    UserForm,
    VerifyOTPForm,
)
from .models import EmailOTP
from .permissions import is_admin, is_guide
from .services import send_otp_email


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["initial_mode"] = "sign-in"
        context["login_form"] = context.get("form")
        if "signup_form" not in context:
            context["signup_form"] = SignUpForm()
        context["next"] = self.request.GET.get("next") or self.request.POST.get("next") or ""
        return context


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:redirect")
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # saved with is_active=False
            otp = EmailOTP.generate_otp(email=user.email, purpose=EmailOTP.Purpose.SIGNUP, user=user)
            send_otp_email(otp)
            request.session["otp_signup_email"] = user.email
            request.session["otp_signup_next"] = next_url
            messages.info(
                request,
                f"We've sent a 6-digit verification code to {user.email}. Please verify your email to complete registration.",
            )
            return redirect("accounts:verify_signup_otp")
        return render(
            request,
            "accounts/signup.html",
            {
                "form": form,
                "signup_form": form,
                "login_form": LoginForm(),
                "initial_mode": "sign-up",
                "next": next_url,
            },
        )
    return render(
        request,
        "accounts/signup.html",
        {
            "form": SignUpForm(),
            "signup_form": SignUpForm(),
            "login_form": LoginForm(),
            "initial_mode": "sign-up",
            "next": next_url,
        },
    )


def verify_signup_otp(request):
    if request.user.is_authenticated:
        return redirect("accounts:redirect")
    email = request.session.get("otp_signup_email")
    next_url = request.session.get("otp_signup_next") or ""
    if not email:
        messages.warning(request, "Please create an account first to verify your email.")
        return redirect("accounts:signup")

    user = User.objects.filter(email__iexact=email, is_active=False).first()
    if not user:
        active_user = User.objects.filter(email__iexact=email, is_active=True).first()
        if active_user:
            messages.info(request, "Your email is already verified! Please sign in.")
            request.session.pop("otp_signup_email", None)
            return redirect("accounts:login")
        messages.warning(request, "Account registration not found. Please sign up again.")
        return redirect("accounts:signup")

    form = VerifyOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        success, result = EmailOTP.verify_otp(email, code, EmailOTP.Purpose.SIGNUP)
        if success:
            user.is_active = True
            user.save(update_fields=["is_active"])
            login(request, user)
            request.session.pop("otp_signup_email", None)
            request.session.pop("otp_signup_next", None)
            display_name = user.first_name or user.username
            messages.success(request, f"Welcome aboard, {display_name}! Your email has been verified.")
            return redirect(next_url or "accounts:bookings")
        else:
            messages.error(request, result)

    return render(
        request,
        "accounts/verify_otp.html",
        {
            "email": email,
            "form": form,
            "purpose": EmailOTP.Purpose.SIGNUP,
            "title": "Verify your email",
        },
    )


def forgot_password(request):
    """Handle forgot password requests and send an OTP code."""
    if request.user.is_authenticated:
        return redirect("accounts:redirect")
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                otp = EmailOTP.generate_otp(email=email, purpose=EmailOTP.Purpose.RESET_PASSWORD, user=user)
                send_otp_email(otp)
            request.session["otp_reset_email"] = email
            messages.info(
                request,
                f"If an account exists with {email}, a 6-digit password reset code has been sent to your inbox.",
            )
            return redirect("accounts:reset_password")
        else:
            messages.warning(request, "Please enter a valid email address.")
            return redirect("accounts:login")

    form = ForgotPasswordForm()
    return render(request, "accounts/forgot_password.html", {"form": form})


def reset_password(request):
    """Verify OTP and set a new password."""
    if request.user.is_authenticated:
        return redirect("accounts:redirect")
    email_from_session = request.session.get("otp_reset_email", "")

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            code = form.cleaned_data["code"]
            new_password = form.cleaned_data["new_password"]

            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if not user:
                messages.error(request, "No active account found with this email address.")
            else:
                success, result = EmailOTP.verify_otp(email, code, EmailOTP.Purpose.RESET_PASSWORD)
                if success:
                    user.set_password(new_password)
                    user.save()
                    request.session.pop("otp_reset_email", None)
                    messages.success(
                        request,
                        "Your password has been reset successfully! You can now sign in with your new password.",
                    )
                    return redirect("accounts:login")
                else:
                    messages.error(request, result)
    else:
        form = ResetPasswordForm(initial={"email": email_from_session})

    return render(
        request,
        "accounts/reset_password.html",
        {
            "form": form,
            "email": email_from_session,
        },
    )


def resend_otp(request):
    """Resend a fresh OTP verification code with rate limiting."""
    if request.method != "POST":
        return redirect("accounts:login")
    purpose = request.POST.get("purpose", "").strip()
    email = request.POST.get("email", "").strip().lower()

    if purpose == EmailOTP.Purpose.SIGNUP:
        session_email = request.session.get("otp_signup_email")
        email = email or session_email
        redirect_view = "accounts:verify_signup_otp"
    elif purpose == EmailOTP.Purpose.RESET_PASSWORD:
        session_email = request.session.get("otp_reset_email")
        email = email or session_email
        redirect_view = "accounts:reset_password"
    else:
        messages.error(request, "Invalid verification request.")
        return redirect("accounts:login")

    if not email:
        messages.warning(request, "Email address not found. Please try again.")
        return redirect("accounts:login")

    # Rate limiting: 45 seconds cooldown
    recent = EmailOTP.objects.filter(
        email__iexact=email,
        purpose=purpose,
        created_at__gte=timezone.now() - timedelta(seconds=45),
    ).first()
    if recent:
        messages.warning(request, "Please wait 45 seconds before requesting another code.")
        return redirect(redirect_view)

    user = User.objects.filter(email__iexact=email).first()
    otp = EmailOTP.generate_otp(email=email, purpose=purpose, user=user)
    send_otp_email(otp)
    messages.success(request, f"A fresh 6-digit verification code has been sent to {email}.")
    return redirect(redirect_view)


@login_required
def role_redirect(request):
    """Send each user to the right home after login."""
    if is_admin(request.user):
        return redirect("dashboard:home")
    if is_guide(request.user):
        return redirect("guide:home")
    return redirect("accounts:bookings")


@login_required
def my_bookings(request):
    bookings = request.user.bookings.select_related("tour", "tour__destination").order_by("-travel_date")
    return render(request, "accounts/bookings.html", {"bookings": bookings})


@login_required
def cancel_booking(request, reference):
    booking = request.user.bookings.filter(reference=reference).first()
    if request.method == "POST" and booking and booking.can_cancel:
        services.cancel_booking(booking, by=request.user)
        messages.info(request, f"Booking {booking.reference} has been cancelled.")
    return redirect("accounts:bookings")


@login_required
def booking_detail(request, reference):
    """Customer hub for one booking: status, payment, traveler names and chat with the guide."""
    booking = get_object_or_404(
        request.user.bookings.select_related("tour", "tour__destination", "guide__profile"), reference=reference
    )
    editable = booking.status != booking.Status.CANCELLED and booking.is_upcoming
    formset = ParticipantFormSet(request.POST or None, instance=booking, prefix="p")
    formset.max_num = booking.travelers
    if request.method == "POST" and editable and formset.is_valid():
        kept = [f for f in formset.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        if len(kept) > booking.travelers:
            messages.error(request, f"This booking is for {booking.travelers} traveler(s).")
        else:
            formset.save()
            messages.success(request, "Traveler details saved - your guide can see them now.")
            return redirect(booking.get_absolute_url() + "#travelers")
    return render(request, "accounts/booking_detail.html", {"booking": booking, "formset": formset, "editable": editable})


@login_required
def inbox(request):
    return render(request, "accounts/inbox.html", {"threads": threads_for(request.user)})


@login_required
def profile(request):
    user_form = UserForm(request.POST or None, instance=request.user)
    profile_form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"user_form": user_form, "profile_form": profile_form})
