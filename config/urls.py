from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "GoTrip administration"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("core.urls")),
    path("account/", include("accounts.urls")),
    path("tours/", include("tours.urls")),
    path("blog/", include("blog.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("guide/", include("guide.urls")),
    path("chatbot/", include("chatbot.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = 'core.views.page_not_found'
