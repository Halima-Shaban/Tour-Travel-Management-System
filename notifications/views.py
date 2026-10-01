from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.permissions import is_admin, is_guide


@login_required
def notification_list(request):
    page = Paginator(request.user.notifications.all(), 20).get_page(request.GET.get("page"))
    if is_admin(request.user):
        layout = "dashboard/_base.html"
    elif is_guide(request.user):
        layout = "guide/_base.html"
    else:
        layout = "base.html"
    return render(request, "notifications/list.html", {"page": page, "layout": layout, "public": layout == "base.html"})


@login_required
def open_notification(request, pk):
    notification = get_object_or_404(request.user.notifications, pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    target = notification.url
    if not target or not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "notifications:list"
    return redirect(target)


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER") or "notifications:list")
