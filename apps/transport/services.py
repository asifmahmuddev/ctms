"""Geocoding and routing, answered by OpenRouteService and by great-circle geometry.

Every call is made from the server, so the key never reaches a browser. The service routes roads
only, so the other modes, and any road route it declines, follow a straight line.
"""

import json
import logging
import math

import requests
from django.conf import settings

from .models import EARTH_RADIUS_METRES, TransportMode, cruising_speed_metres_per_second

GEOCODE_URL = 'https://api.openrouteservice.org/geocode/autocomplete'
DIRECTIONS_URL = 'https://api.openrouteservice.org/v2/directions/{profile}/geojson'

# A routing profile per vehicle; only land modes have one, the rest are drawn as a direct line.
ROUTING_PROFILES = {
    TransportMode.ROAD: 'driving-hgv',
    TransportMode.RAIL: 'driving-car',
}

# The lorry profile's time stands; the car profile only shapes a rail corridor, so rail is retimed.
MODES_TIMED_BY_THE_SERVICE = {TransportMode.ROAD}

SUGGESTION_COUNT = 5
GEOCODE_LANGUAGE = 'en'

# A routed line has thousands of points, so thinning keeps the shape at a fraction of the size.
MAXIMUM_ROUTE_POINTS = 200
COORDINATE_PRECISION = 5

# Points on a direct line, enough that a great circle reads as a curve rather than as a chord.
DIRECT_LINE_POINTS = 64

logger = logging.getLogger(__name__)


class Route:
    """A journey between two places: how far, how long, and the line it takes on a map."""

    def __init__(self, distance_metres, duration_seconds, points, is_direct):
        self.distance_metres = distance_metres
        self.duration_seconds = duration_seconds
        self.points = points
        self.is_direct = is_direct


def great_circle_metres(origin, destination):
    """Return the distance over the earth's surface between two (latitude, longitude) pairs."""

    origin_latitude, origin_longitude = (math.radians(value) for value in origin)
    destination_latitude, destination_longitude = (math.radians(value) for value in destination)

    latitude_span = destination_latitude - origin_latitude
    longitude_span = destination_longitude - origin_longitude

    chord = (
        math.sin(latitude_span / 2) ** 2
        + math.cos(origin_latitude) * math.cos(destination_latitude) * math.sin(longitude_span / 2) ** 2
    )
    return round(EARTH_RADIUS_METRES * 2 * math.asin(math.sqrt(chord)))


def great_circle_points(origin, destination, count=DIRECT_LINE_POINTS):
    """Return points along the shortest path over the earth between two (latitude, longitude) pairs.

    Interpolating along the sphere makes a long journey bend the way an aircraft or ship travels.
    """

    origin_latitude, origin_longitude = (math.radians(value) for value in origin)
    destination_latitude, destination_longitude = (math.radians(value) for value in destination)

    angle = great_circle_metres(origin, destination) / EARTH_RADIUS_METRES
    if not angle:
        return [rounded(origin), rounded(destination)]

    points = []
    for step in range(count + 1):
        fraction = step / count
        start_share = math.sin((1 - fraction) * angle) / math.sin(angle)
        end_share = math.sin(fraction * angle) / math.sin(angle)

        x = start_share * math.cos(origin_latitude) * math.cos(origin_longitude) + end_share * math.cos(destination_latitude) * math.cos(destination_longitude)
        y = start_share * math.cos(origin_latitude) * math.sin(origin_longitude) + end_share * math.cos(destination_latitude) * math.sin(destination_longitude)
        z = start_share * math.sin(origin_latitude) + end_share * math.sin(destination_latitude)

        points.append(rounded((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x)))))

    return points


def rounded(point):
    """Return one (latitude, longitude) pair at the precision a stored route keeps."""

    latitude, longitude = point
    return [round(latitude, COORDINATE_PRECISION), round(longitude, COORDINATE_PRECISION)]


def thinned(points):
    """Return at most `MAXIMUM_ROUTE_POINTS` of a routed line, always keeping where it ends."""

    if len(points) <= MAXIMUM_ROUTE_POINTS:
        kept = points
    else:
        step = math.ceil(len(points) / MAXIMUM_ROUTE_POINTS)
        kept = points[::step]

    if kept[-1] != points[-1]:
        kept = [*kept, points[-1]]

    return kept


def suggest_places(text):
    """Return places matching what has been typed, each with the coordinates it sits at.

    A failure costs only the suggestions, so an empty list is returned and the address can be typed.
    """

    try:
        response = requests.get(
            GEOCODE_URL,
            params={'api_key': settings.OPENROUTESERVICE_API_KEY, 'text': text,
                    'size': SUGGESTION_COUNT, 'lang': GEOCODE_LANGUAGE},
            timeout=settings.ROUTING_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        features = response.json().get('features', [])
    except (requests.RequestException, ValueError):
        logger.exception('Unable to look up places matching "%s"', text)
        return []

    places = []
    for feature in features:
        longitude, latitude = feature['geometry']['coordinates']
        places.append({'label': feature['properties']['label'], 'latitude': latitude, 'longitude': longitude})

    return places


def routed_over_land(profile, origin, destination):
    """Return the road route between two places, or None when the service will not answer for it.

    Declining a long journey, or finding no road at all, are ordinary answers rather than faults.
    """

    try:
        response = requests.post(
            DIRECTIONS_URL.format(profile=profile),
            json={'coordinates': [[origin[1], origin[0]], [destination[1], destination[0]]], 'geometry_simplify': True},
            headers={'Authorization': settings.OPENROUTESERVICE_API_KEY, 'Content-Type': 'application/json'},
            timeout=settings.ROUTING_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        feature = response.json()['features'][0]

        summary = feature['properties']['summary']
        points = thinned([rounded((latitude, longitude)) for longitude, latitude in feature['geometry']['coordinates']])
    except (requests.RequestException, KeyError, IndexError, ValueError):
        logger.info('No road route between %s and %s; falling back to the direct line', origin, destination)
        return None

    return Route(
        distance_metres=round(summary['distance']),
        duration_seconds=round(summary['duration']),
        points=points,
        is_direct=False,
    )


def find_route(mode, origin, destination):
    """Return the journey a consignment takes between two (latitude, longitude) pairs.

    Land modes route over roads where the service can; the rest follow the great circle at mode speed.
    """

    profile = ROUTING_PROFILES.get(mode)
    if profile:
        route = routed_over_land(profile, origin, destination)
        if route:
            if mode not in MODES_TIMED_BY_THE_SERVICE:
                route.duration_seconds = round(route.distance_metres / cruising_speed_metres_per_second(mode))

            return route

    distance = great_circle_metres(origin, destination)
    return Route(
        distance_metres=distance,
        duration_seconds=round(distance / cruising_speed_metres_per_second(mode)),
        points=great_circle_points(origin, destination),
        is_direct=True,
    )


def encode_points(points):
    """Return the compact JSON a route's line is stored as."""

    return json.dumps(points, separators=(',', ':'))
