"""Views for placing, listing, reading and cancelling an account's transport orders."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView

from apps.common.lists import FilterGroup, RecordListView

from .forms import TransportOrderForm
from .models import CURRENCY_SYMBOL, MINIMUM_ORDER_COST, OrderStatus, TransportMode, TransportOrder, rate_card
from .services import encode_points, find_route, suggest_places

ORDER_FORM_TEMPLATE = 'transport/order-form.html'
ORDER_LIST_TEMPLATE = 'transport/order-list.html'
ORDER_DETAIL_TEMPLATE = 'transport/order-detail.html'

MINIMUM_COST_LABEL = f'{CURRENCY_SYMBOL}{MINIMUM_ORDER_COST}'

# Below this, a search is too broad to be worth asking the geocoder about.
MINIMUM_SUGGESTION_LENGTH = 3

ORDER_PLACED_MESSAGE = 'Order {reference} has been placed. We will confirm it shortly.'
ORDER_CANCELLED_MESSAGE = 'Order {reference} has been cancelled.'
ORDER_NOT_CANCELLABLE_MESSAGE = 'Order {reference} is already under way and can no longer be cancelled.'


class OwnOrdersMixin(LoginRequiredMixin):
    """Restricts every lookup to the signed-in account's own orders.

    Filtering the queryset answers another account's order with a 404, telling the asker nothing.
    """

    model = TransportOrder

    def get_queryset(self):
        return super().get_queryset().filter(account=self.request.user)


class TransportOrderCreateView(LoginRequiredMixin, CreateView):
    """Places an order for the signed-in account."""

    form_class = TransportOrderForm
    template_name = ORDER_FORM_TEMPLATE

    def get_context_data(self, **kwargs):
        """Quote the rates alongside the form, from the same table the saved order is priced by."""

        return super().get_context_data(rates=rate_card(), minimum_cost=MINIMUM_COST_LABEL, **kwargs)

    def form_valid(self, form):
        # Saved against the signed-in account; cost and status are the model's, not the form's.
        order = form.save(commit=False)
        order.account = self.request.user
        self.attach_route(order, form)
        order.save()

        self.object = order
        messages.success(self.request, ORDER_PLACED_MESSAGE.format(reference=order.reference))
        return redirect(order.get_absolute_url())

    @staticmethod
    def attach_route(order, form):
        """Work out the journey between the two places, when both were picked from the suggestions.

        A hand-typed address carries no coordinates, so the order is stored without a route, not refused.
        """

        origin = form.coordinates('origin')
        destination = form.coordinates('destination')
        if not origin or not destination:
            return

        route = find_route(order.mode, origin, destination)

        order.origin_latitude, order.origin_longitude = origin
        order.destination_latitude, order.destination_longitude = destination
        order.distance_metres = route.distance_metres
        order.duration_seconds = route.duration_seconds
        order.route_points = encode_points(route.points)
        order.route_is_direct = route.is_direct


@require_GET
@login_required
def place_suggestions(request):
    """Answer the order form's address box with places matching what has been typed.

    The lookup runs here rather than in the browser, so the routing service's key stays on the server.
    """

    text = request.GET.get('q', '').strip()
    places = suggest_places(text) if len(text) >= MINIMUM_SUGGESTION_LENGTH else []
    return JsonResponse({'places': places})


class TransportOrderListView(OwnOrdersMixin, RecordListView):
    """Lists the signed-in account's orders, searchable, narrowable and reorderable like every table."""

    template_name = ORDER_LIST_TEMPLATE
    context_object_name = 'orders'

    search_fields = ('origin', 'destination', 'payment__reference')
    search_placeholder = 'Search by place or receipt'
    filter_groups = (
        FilterGroup('status', 'All statuses', tuple((status.value, status.label, Q(status=status.value)) for status in OrderStatus)),
        FilterGroup('mode', 'All modes', tuple((mode.value, mode.label, Q(mode=mode.value)) for mode in TransportMode)),
    )
    sort_options = (
        ('newest', 'Newest first', ('-placed_at',)),
        ('oldest', 'Oldest first', ('placed_at',)),
        ('dearest', 'Cost, highest first', ('-cost',)),
        ('cheapest', 'Cost, lowest first', ('cost',)),
        ('heaviest', 'Weight, heaviest first', ('-weight_kilograms',)),
    )


class TransportOrderDetailView(OwnOrdersMixin, DetailView):
    """Shows one of the signed-in account's orders in full."""

    template_name = ORDER_DETAIL_TEMPLATE
    context_object_name = 'order'


@login_required
@require_POST
def cancel_order(request, pk):
    """Call off an order that has not been picked up. POST only, so no link can trigger it."""

    order = get_object_or_404(TransportOrder, pk=pk, account=request.user)
    if order.can_be_cancelled:
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=['status'])
        messages.success(request, ORDER_CANCELLED_MESSAGE.format(reference=order.reference))
    else:
        messages.error(request, ORDER_NOT_CANCELLABLE_MESSAGE.format(reference=order.reference))

    return redirect(order.get_absolute_url())
