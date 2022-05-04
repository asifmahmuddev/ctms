"""Transport order model, the modes it can be shipped by, and how an order is priced."""

import json
import math

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

MAX_LENGTH_CHOICE = 16
MAX_LENGTH_PLACE = 128

MINIMUM_ORDER_COST = 25
MINIMUM_WEIGHT_KILOGRAMS = 0.1
MAXIMUM_WEIGHT_KILOGRAMS = 100000

# Weighed to the nearest ten grams, the precision stored, priced and shown.
WEIGHT_DECIMAL_PLACES = 2

CURRENCY_SYMBOL = '$'
DEFAULT_MODE_ICON = 'fa-box'

EARTH_RADIUS_METRES = 6371008
METRES_PER_KILOMETRE = 1000
SECONDS_PER_HOUR = 3600
MINUTES_PER_HOUR = 60

# How each stage of an order reads on the tracker: behind it, at it, or still ahead of it.
PROGRESS_DONE = 'done'
PROGRESS_CURRENT = 'current'
PROGRESS_UPCOMING = 'upcoming'


class TransportMode(models.TextChoices):
    """The ways a consignment can travel."""

    AIR = 'air', 'Airplane'
    SEA = 'sea', 'Ship'
    ROAD = 'road', 'Truck'
    RAIL = 'rail', 'Rail'


class OrderStatus(models.TextChoices):
    """Where an order stands: the stages it runs through, then the three ways it can end early."""

    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    PROCESSING = 'processing', 'Processing'
    READY_FOR_PICKUP = 'ready-for-pickup', 'Ready for Pickup'
    PICKED_UP = 'picked-up', 'Picked Up'
    IN_TRANSIT = 'in-transit', 'In Transit'
    OUT_FOR_DELIVERY = 'out-for-delivery', 'Out for Delivery'
    DELIVERED = 'delivered', 'Delivered'
    COMPLETED = 'completed', 'Completed'

    CANCELLED = 'cancelled', 'Cancelled'
    RETURNED = 'returned', 'Returned'
    ARCHIVED = 'archived', 'Archived'


# Keyed on the members, not their values, so renaming a mode cannot leave a map behind.
COST_PER_KILOGRAM = {
    TransportMode.AIR: 9,
    TransportMode.SEA: 2,
    TransportMode.ROAD: 4,
    TransportMode.RAIL: 3,
}

# Roughly how fast each mode travels, for the journeys no routing service will answer.
CRUISING_SPEED_KILOMETRES_PER_HOUR = {
    TransportMode.AIR: 850,
    TransportMode.SEA: 40,
    TransportMode.ROAD: 65,
    TransportMode.RAIL: 80,
}

# Per kilogram as well as per thousand kilometres, so a heavy load pays for the distance.
COST_PER_KILOGRAM_PER_THOUSAND_KILOMETRES = {
    TransportMode.AIR: 1.20,
    TransportMode.SEA: 0.04,
    TransportMode.ROAD: 0.35,
    TransportMode.RAIL: 0.22,
}

METRES_PER_THOUSAND_KILOMETRES = METRES_PER_KILOMETRE * 1000

# Font Awesome names, held here so a template never decides which icon a mode wears.
MODE_ICONS = {
    TransportMode.AIR: 'fa-plane',
    TransportMode.SEA: 'fa-ship',
    TransportMode.ROAD: 'fa-truck',
    TransportMode.RAIL: 'fa-train',
}

# The home page's example: only what a person would type, the rest worked out from the rates above.
SAMPLE_ORIGIN = 'Dhaka, BD'
SAMPLE_DESTINATION = 'Rotterdam, NL'
SAMPLE_MODE = TransportMode.AIR
SAMPLE_WEIGHT_KILOGRAMS = 340
SAMPLE_DISTANCE_METRES = 7_400_000

# The stages an order runs through. Ending early is not a point along the track, so it is not here.
PROGRESS_STATUSES = (
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.PROCESSING,
    OrderStatus.READY_FOR_PICKUP,
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED,
    OrderStatus.COMPLETED,
)

ENDED_STATUSES = (OrderStatus.CANCELLED, OrderStatus.RETURNED, OrderStatus.ARCHIVED)

# The owner calls an order off only before the desk confirms it; from then on it is the desk's.
OWNER_CANCELLABLE_STATUSES = (OrderStatus.PENDING,)

# What each stage wears on the tracker, held here so no template decides what a stage looks like.
STATUS_ICONS = {
    OrderStatus.PENDING: 'fa-hourglass-start',
    OrderStatus.CONFIRMED: 'fa-clipboard-check',
    OrderStatus.PROCESSING: 'fa-cogs',
    OrderStatus.READY_FOR_PICKUP: 'fa-box-open',
    OrderStatus.PICKED_UP: 'fa-dolly',
    OrderStatus.IN_TRANSIT: 'fa-shipping-fast',
    OrderStatus.OUT_FOR_DELIVERY: 'fa-truck-loading',
    OrderStatus.DELIVERED: 'fa-check-double',
    OrderStatus.COMPLETED: 'fa-flag-checkered',
    OrderStatus.CANCELLED: 'fa-ban',
    OrderStatus.RETURNED: 'fa-undo',
    OrderStatus.ARCHIVED: 'fa-archive',
}


def money_label(amount):
    """Return an amount written the way every price on the site is written."""

    return f'{CURRENCY_SYMBOL}{amount:,}'


def weight_label(kilograms):
    """Return a weight without trailing zeros, so a whole number of kilograms reads as one."""

    return f'{kilograms:,.{WEIGHT_DECIMAL_PLACES}f}'.rstrip('0').rstrip('.') + ' kg'


def distance_label(metres):
    """Return a distance in whole kilometres, or nothing when none was worked out."""

    return f'{metres / METRES_PER_KILOMETRE:,.0f} km' if metres else ''


def duration_label(seconds):
    """Return a journey time in hours and minutes, leaving out whichever of them is zero."""

    if not seconds:
        return ''

    minutes = round(seconds / SECONDS_PER_HOUR * MINUTES_PER_HOUR)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    if hours and minutes:
        return f'{hours:,} h {minutes} min'

    return f'{hours:,} h' if hours else f'{minutes} min'


def cruising_speed_metres_per_second(mode):
    """Return how fast a mode travels, in the units a duration is worked out in."""

    return CRUISING_SPEED_KILOMETRES_PER_HOUR[mode] * METRES_PER_KILOMETRE / SECONDS_PER_HOUR


def rate_card():
    """Return every mode with both of the rates it is charged at, for a page that quotes before ordering."""

    return [
        {
            'label': mode.label,
            'icon': MODE_ICONS[mode],
            'weight_rate': f'{CURRENCY_SYMBOL}{cost}',
            'distance_rate': f'{CURRENCY_SYMBOL}{COST_PER_KILOGRAM_PER_THOUSAND_KILOMETRES[mode]:.2f}',
        }
        for mode, cost in COST_PER_KILOGRAM.items()
    ]


def service_figures():
    """Return the counts the about page quotes, read from the definitions rather than written down.

    A typed figure cannot follow what it counts, so each is derived from the choices themselves.
    """

    return {
        'modes': len(TransportMode.choices),
        'stages': len(PROGRESS_STATUSES),
        'statuses': len(OrderStatus.choices),
    }


def sample_consignment():
    """Return the example shown on the home page, priced and timed the way a real order would be.

    Priced from the rate card and timed at cruising speed, so it never quotes figures the site would not.
    """

    mode = SAMPLE_MODE
    distance = SAMPLE_DISTANCE_METRES
    weight = SAMPLE_WEIGHT_KILOGRAMS

    return {
        'origin': SAMPLE_ORIGIN,
        'destination': SAMPLE_DESTINATION,
        'mode_label': mode.label,
        'mode_icon': MODE_ICONS[mode],
        'weight': weight_label(weight),
        'distance': distance_label(distance),
        'duration': duration_label(distance / cruising_speed_metres_per_second(mode)),
        'cost': money_label(quote_cost(mode, weight, distance)),
    }


def quote_cost(mode, weight_kilograms, distance_metres=None):
    """Return what a consignment costs to move, never less than the minimum an order is worth.

    Without a route it is charged on weight alone, and a part unit is charged whole, never rounding down.
    """

    carriage = COST_PER_KILOGRAM[mode] * weight_kilograms
    haulage = 0.0

    if distance_metres:
        thousands = distance_metres / METRES_PER_THOUSAND_KILOMETRES
        haulage = COST_PER_KILOGRAM_PER_THOUSAND_KILOMETRES[mode] * weight_kilograms * thousands

    return max(MINIMUM_ORDER_COST, math.ceil(carriage + haulage))


class TransportOrder(models.Model):
    """One consignment an account has asked to have moved.

    Cost and status are set by the server from the mode and weight, never accepted from the browser.
    """

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transport_orders')
    placed_at = models.DateTimeField(auto_now_add=True)

    mode = models.CharField(max_length=MAX_LENGTH_CHOICE, choices=TransportMode.choices)
    origin = models.CharField(max_length=MAX_LENGTH_PLACE)
    destination = models.CharField(max_length=MAX_LENGTH_PLACE)
    weight_kilograms = models.FloatField(
        validators=[MinValueValidator(MINIMUM_WEIGHT_KILOGRAMS), MaxValueValidator(MAXIMUM_WEIGHT_KILOGRAMS)],
    )

    # Settled when the order is placed; a route is not always available, so each may be unset.
    origin_latitude = models.FloatField(blank=True, null=True)
    origin_longitude = models.FloatField(blank=True, null=True)
    destination_latitude = models.FloatField(blank=True, null=True)
    destination_longitude = models.FloatField(blank=True, null=True)

    distance_metres = models.PositiveIntegerField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)

    # The line the journey takes, as JSON latitude and longitude pairs for the map to draw.
    route_points = models.TextField(blank=True, null=True)
    route_is_direct = models.BooleanField(default=False)

    cost = models.PositiveIntegerField()

    status = models.CharField(max_length=MAX_LENGTH_CHOICE, choices=OrderStatus.choices, default=OrderStatus.PENDING)

    class Meta:
        ordering = ('-placed_at',)

    def __str__(self):
        return f'{self.get_mode_display()} from {self.origin} to {self.destination}'

    def save(self, *args, **kwargs):
        """Settle the weight and price it, so what is stored, charged and shown are the same figures.

        The price is worked out afresh every time, from the mode, the weight and the journey.
        """

        self.weight_kilograms = round(self.weight_kilograms, WEIGHT_DECIMAL_PLACES)
        self.cost = quote_cost(self.mode, self.weight_kilograms, self.distance_metres)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('order_detail', kwargs={'pk': self.pk})

    @property
    def reference(self):
        """Return the code an account quotes when asking about this order."""

        return f'CTMS-{self.pk}'

    @property
    def mode_icon(self):
        return MODE_ICONS.get(self.mode, DEFAULT_MODE_ICON)

    @property
    def cost_label(self):
        return money_label(self.cost)

    @property
    def weight_label(self):
        return weight_label(self.weight_kilograms)

    @property
    def has_route(self):
        """Return whether this order knows the journey it takes."""

        return self.distance_metres is not None and bool(self.route_points)

    @property
    def route_line(self):
        """Return the stored line as coordinate pairs, or nothing when no route was worked out."""

        return json.loads(self.route_points) if self.route_points else []

    @property
    def distance_label(self):
        return distance_label(self.distance_metres)

    @property
    def duration_label(self):
        return duration_label(self.duration_seconds)

    @property
    def progress(self):
        """Return the stages of this order, each marked as passed, current or still ahead.

        An order that ended early left the track, so it reports no stages and draws no tracker.
        """

        if self.status in ENDED_STATUSES:
            return []

        reached = PROGRESS_STATUSES.index(self.status)
        return [
            {
                'label': status.label,
                'icon': STATUS_ICONS[status],
                'state': PROGRESS_DONE if index < reached else PROGRESS_CURRENT if index == reached else PROGRESS_UPCOMING,
            }
            for index, status in enumerate(PROGRESS_STATUSES)
        ]

    @property
    def status_icon(self):
        """Return the mark this order's own status wears, wherever it is shown on its own."""

        return STATUS_ICONS[OrderStatus(self.status)]

    @property
    def has_ended(self):
        """Return whether this order left the track rather than running it to the end."""

        return self.status in ENDED_STATUSES

    @property
    def can_be_cancelled(self):
        """Return whether the owner may still call this order off.

        The window closes when the desk confirms it; from then on cancelling is the desk's, at any point.
        """

        return self.status in OWNER_CANCELLABLE_STATUSES
