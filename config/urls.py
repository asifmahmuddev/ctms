"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

FAVICON_URL = f'{settings.STATIC_URL}images/favicon.ico'

urlpatterns = [
    # Browsers ask for this path on any page that declares no icon of its own, error pages included.
    path('favicon.ico', RedirectView.as_view(url=FAVICON_URL)),
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('', include('apps.pages.urls')),
]

if settings.DEBUG:
    # Nothing else serves uploaded files, so profile images resolve only under the dev server.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
