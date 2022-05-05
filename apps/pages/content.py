"""Copy for the public information pages, held together rather than spread through their templates."""

from apps.transport.models import (
    COST_PER_KILOGRAM,
    COST_PER_KILOGRAM_PER_THOUSAND_KILOMETRES,
    CRUISING_SPEED_KILOMETRES_PER_HOUR,
    MODE_ICONS,
    TransportMode,
)

# Each service is named for the mode it books, so a footer link and a heading cannot drift apart.
SERVICE_NAME = '{mode} freight'
SERVICE_ANCHOR = '{mode}-freight'

SERVICE_DESCRIPTIONS = {
    TransportMode.AIR: 'The quickest way between continents, and the one that keeps a schedule when a deadline will not move.',
    TransportMode.SEA: 'The cheapest way to move weight in quantity, for cargo whose delivery date is measured in weeks.',
    TransportMode.ROAD: 'Door to door with no handover in between, and the only mode that reaches an address rather than a terminal.',
    TransportMode.RAIL: 'Overland haulage at a fraction of a lorry fleet, for freight travelling a corridor rather than a route.',
}

SERVICE_SUITS = {
    TransportMode.AIR: ('Perishables and pharmaceuticals', 'Urgent replacement parts', 'High value at low weight'),
    TransportMode.SEA: ('Raw materials in bulk', 'Full container loads', 'Stock replenished to a plan'),
    TransportMode.ROAD: ('Regional distribution', 'Final delivery to the door', 'Consignments split across drops'),
    TransportMode.RAIL: ('Heavy freight overland', 'Scheduled corridor traffic', 'Bulk that is not time-critical'),
}

# What a visitor is told about the platform itself, beneath the four services.
SERVICE_PROMISES = (
    ('fa-calculator', 'Priced before you book', 'Every quote is worked out from the mode, the weight and the distance, and is the price the order is placed at.'),
    ('fa-route', 'Routed, not estimated', 'Road and rail are measured over the road network; sea and air follow the great circle, and the order says which it drew.'),
    ('fa-eye', 'Visible end to end', 'An order moves from pending through processing to complete, and its owner sees each step as the freight desk records it.'),
)

# Careers. No role names a person, and each one applies through the contact page.
CAREER_VALUES = (
    ('fa-people-carry', 'Freight first', 'Everyone here spends time with the operations desk. The people who build the platform understand the work it does.'),
    ('fa-seedling', 'Room to grow', 'Small teams with real ownership. You will ship work that customers use in the week you write it.'),
    ('fa-balance-scale', 'Sensible hours', 'Freight runs around the clock; the people planning it do not have to. Cover is rostered, not assumed.'),
)

OPEN_ROLES = (
    {
        'title': 'Freight Operations Coordinator',
        'team': 'Operations',
        'location': 'Dhaka',
        'arrangement': 'Full time',
        'summary': 'Work the order book end to end: confirm bookings, keep statuses honest and stay ahead of the exceptions before a customer has to ask.',
    },
    {
        'title': 'Backend Engineer',
        'team': 'Engineering',
        'location': 'Dhaka or remote',
        'arrangement': 'Full time',
        'summary': 'Build the quoting, routing and tracking the platform runs on, and the interfaces the freight desk works in every day.',
    },
    {
        'title': 'Customer Support Specialist',
        'team': 'Support',
        'location': 'Dhaka',
        'arrangement': 'Full time',
        'summary': 'Answer the enquiries that arrive through the contact desk, and turn the questions we keep getting into answers nobody has to ask for.',
    },
    {
        'title': 'Route Planning Analyst',
        'team': 'Operations',
        'location': 'Dhaka',
        'arrangement': 'Part time',
        'summary': 'Study how our freight actually travels, and tune the corridors, modes and rates that decide what a consignment is quoted.',
    },
)

APPLICATION_SUBJECT = 'Application: {role}'


def freight_services():
    """Return each mode with its copy and the rates an order placed that way is actually charged.

    Read from the transport app, so the page cannot quote a price the platform does not charge.
    """

    return [
        {
            'anchor': SERVICE_ANCHOR.format(mode=mode.value),
            'name': SERVICE_NAME.format(mode=mode.value).capitalize(),
            'icon': MODE_ICONS[mode],
            'carrier': mode.label,
            'description': SERVICE_DESCRIPTIONS[mode],
            'suits': SERVICE_SUITS[mode],
            'cost_per_kilogram': COST_PER_KILOGRAM[mode],
            'cost_per_thousand_kilometres': COST_PER_KILOGRAM_PER_THOUSAND_KILOMETRES[mode],
            'cruising_speed': CRUISING_SPEED_KILOMETRES_PER_HOUR[mode],
        }
        for mode in TransportMode
    ]


def open_roles():
    """Return the roles being advertised, each carrying the subject its application arrives under."""

    return [{**role, 'subject': APPLICATION_SUBJECT.format(role=role['title'])} for role in OPEN_ROLES]
