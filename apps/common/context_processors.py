"""Values every template may need, regardless of which view rendered it."""

from django.conf import settings

from apps.company.models import CompanyProfile

GOOGLE_PROVIDER = 'google'


def sign_in_options(_request):
    """Expose which ways in a page may offer, and what the browser needs in order to offer them.

    A provider with no credentials is not advertised, and the request Django passes is unused here.
    """

    google = settings.SOCIALACCOUNT_PROVIDERS[GOOGLE_PROVIDER]['APP']

    return {
        'google_signin_available': bool(google['client_id'] and google['secret']),
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }


def company_details(_request):
    """Expose the company every page names, so no template carries a copy of its own.

    Django passes the request positionally to every context processor; this one has no use for it.
    """

    return {'company': CompanyProfile.current()}
