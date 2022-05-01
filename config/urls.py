"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.pages.urls')),
]

if settings.DEBUG:
    # The development server has no media handler of its own; in production the web server does it.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
