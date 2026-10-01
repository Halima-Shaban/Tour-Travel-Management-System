import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from tours.models import Booking

from .services import can_access, post_message, serialize, thread_for


def _booking(request, reference):
    booking = get_object_or_404(Booking.objects.select_related("user", "guide"), reference=reference)
    if not can_access(request.user, booking):
        raise Http404
    return booking


@login_required
@require_GET
def poll(request, reference):
    """Messages newer than ``?after=<id>`` (all of them when omitted); marks the thread read."""
    thread = thread_for(_booking(request, reference))
    after = request.GET.get("after")
    messages = thread.messages.select_related("sender", "thread__booking")
    if after and after.isdigit():
        messages = messages.filter(pk__gt=int(after))
    thread.mark_read(request.user)
    return JsonResponse({"messages": [serialize(m, request.user) for m in messages]})


@login_required
@require_POST
def send(request, reference):
    booking = _booking(request, reference)
    try:
        body = (json.loads(request.body or "{}").get("body") or "").strip()
    except json.JSONDecodeError:
        body = ""
    if not body:
        return JsonResponse({"error": "Message is empty."}, status=400)
    message = post_message(thread_for(booking), request.user, body)
    return JsonResponse({"message": serialize(message, request.user)})
