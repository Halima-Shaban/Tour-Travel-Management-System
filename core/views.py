from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from blog.models import Post
from tours.forms import TourFilterForm
from tours.models import Booking, Destination, Review, Tour

from .forms import ContactForm, NewsletterForm
from .utils import notify_staff


def home(request):
    context = {
        "search_form": TourFilterForm(),
        "destinations": Destination.objects.filter(is_featured=True)
        .annotate(tour_count=Count("tours", filter=Q(tours__is_active=True)))[:5],
        "featured_tours": Tour.objects.active().filter(is_featured=True).select_related("destination").with_rating()[:6],
        "testimonials": Review.objects.filter(is_approved=True, rating__gte=4).select_related("user", "tour")[:6],
        "posts": Post.objects.published().select_related("author")[:3],
        "stats": {
            "tours": Tour.objects.active().count(),
            "destinations": Destination.objects.count(),
            "travelers": Booking.objects.exclude(status="cancelled").aggregate(n=Sum("travelers"))["n"] or 0,
            "rating": round(Review.objects.filter(is_approved=True).aggregate(v=Avg("rating"))["v"] or 5, 1),
        },
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        msg = form.save()
        notify_staff(f"Contact form: {msg.subject}", f"From {msg.name} <{msg.email}>\n\n{msg.message}")
        messages.success(request, "Thanks! Your message has been sent - we usually reply within a day.")
        return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form})


@require_POST
def newsletter(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "You're subscribed - watch your inbox for travel deals.")
    elif "email" in form.errors and "already exists" in str(form.errors["email"]):
        messages.info(request, "You're already subscribed.")
    else:
        messages.error(request, "Please enter a valid email address.")
    return redirect(request.META.get("HTTP_REFERER") or "core:home")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)
