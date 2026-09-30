from django.conf import settings

from .models import SiteSettings


def site(request):
    return {
        "site": SiteSettings.load(),
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
    }
