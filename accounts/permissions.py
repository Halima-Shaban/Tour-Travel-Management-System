"""Role based access helpers used by the admin and guide dashboards."""
from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import Profile


def get_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return Profile.Role.ADMIN
    profile = getattr(user, "profile", None)
    return profile.role if profile else Profile.Role.CUSTOMER


def is_admin(user):
    return get_role(user) == Profile.Role.ADMIN or (user.is_authenticated and user.is_staff)


def is_guide(user):
    return get_role(user) == Profile.Role.GUIDE


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)


class GuideRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return is_guide(self.request.user)


def role_required(check):
    """Decorator for function views: login for guests, 403 for signed-in users without the role."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required(is_admin)
guide_required = role_required(is_guide)
