"""Values every template may need, regardless of which view rendered it."""

from apps.company.models import CompanyProfile


def company_details(_request):
    """Expose the company every page names, so no template carries a copy of its own.

    Django passes the request positionally to every context processor; this one has no use for it.
    """

    return {'company': CompanyProfile.current()}
