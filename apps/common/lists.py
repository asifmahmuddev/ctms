"""A list view that can be searched, narrowed, reordered and paged from the query string.

Every option is matched against what the page declares before reaching the database, so a hand-edited
address asks only for what is on offer. Submitting by GET makes any view a shareable address.
"""

from collections import namedtuple

from django.db.models import Q
from django.views.generic.list import ListView

SEARCH_PARAMETER = 'q'
SORT_PARAMETER = 'sort'
PAGE_PARAMETER = 'page'

# How many rows a page of any table shows before the next one begins.
ROWS_PER_PAGE = 20

# One narrowing dropdown: the query parameter it reads, the label it wears while nothing is chosen,
# and the (value, label, matches) options it offers. Each group narrows on top of the last.
FilterGroup = namedtuple('FilterGroup', ('parameter', 'label', 'options'))


class RecordListView(ListView):
    """A table with a search box, a narrowing dropdown per group and an ordering dropdown above it."""

    paginate_by = ROWS_PER_PAGE

    search_fields = ()
    search_placeholder = 'Search'
    filter_groups = ()
    sort_options = ()

    def query_without_page(self):
        """Return the query string a page link keeps, so paging does not drop a search or an ordering."""

        query = self.request.GET.copy()
        query.pop(PAGE_PARAMETER, None)
        return query.urlencode()

    def chosen_filters(self):
        """Return what each group was narrowed to, keyed by parameter, ignoring anything not on offer."""

        chosen = {}
        for group in self.filter_groups:
            asked = self.request.GET.get(group.parameter, '')
            chosen[group.parameter] = asked if any(asked == value for value, _, _ in group.options) else ''

        return chosen

    def chosen_sort(self):
        """Return the ordering asked for, falling back to the first one declared."""

        asked = self.request.GET.get(SORT_PARAMETER, '')
        return asked if any(asked == value for value, _, _ in self.sort_options) else self.sort_options[0][0]

    def search_terms(self):
        return self.request.GET.get(SEARCH_PARAMETER, '').strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        terms = self.search_terms()
        if terms:
            matches = Q()
            for field in self.search_fields:
                matches |= Q(**{f'{field}__icontains': terms})

            queryset = queryset.filter(matches)

        chosen = self.chosen_filters()
        for group in self.filter_groups:
            if chosen[group.parameter]:
                queryset = queryset.filter(next(
                    matches for value, _, matches in group.options if value == chosen[group.parameter]))

        ordering = next(fields for value, _, fields in self.sort_options if value == self.chosen_sort())
        return queryset.order_by(*ordering)

    def get_context_data(self, **kwargs):
        chosen = self.chosen_filters()

        return super().get_context_data(
            search_terms=self.search_terms(),
            search_placeholder=self.search_placeholder,
            filter_groups=[
                {
                    'parameter': group.parameter,
                    'label': group.label,
                    'options': [(value, label) for value, label, _ in group.options],
                    'chosen': chosen[group.parameter],
                }
                for group in self.filter_groups
            ],
            narrowed=any(chosen.values()),
            sort_options=[(value, label) for value, label, _ in self.sort_options],
            chosen_sort=self.chosen_sort(),
            page_query=self.query_without_page(),
            **kwargs,
        )
