from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import LoginForm, ProfileForm, SignUpForm, UserForm
from .permissions import is_admin, is_guide


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:redirect")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome aboard, {user.first_name}!")
        return redirect(request.GET.get("next") or "accounts:bookings")
    return render(request, "accounts/signup.html", {"form": form})


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
        booking.status = booking.Status.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        messages.info(request, f"Booking {booking.reference} has been cancelled.")
    return redirect("accounts:bookings")


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
