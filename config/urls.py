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
    # Its own layout reverses routes that are not mounted, so the profile editor answers this.
    path('accounts/social/connections/', RedirectView.as_view(pattern_name='profile_edit')),
    # Only the provider flow is mounted; `allauth.account.urls` duplicates pages this project answers.
    path('accounts/social/', include('allauth.socialaccount.urls')),
    path('accounts/', include('allauth.socialaccount.providers.google.urls')),
    path('backoffice/', include('apps.backoffice.urls')),
    path('', include('apps.billing.urls')),
    path('', include('apps.enquiries.urls')),
    path('', include('apps.pages.urls')),
    path('', include('apps.transport.urls')),
]

if settings.DEBUG:
    # Nothing else serves uploaded files, so profile images resolve only under the dev server.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
