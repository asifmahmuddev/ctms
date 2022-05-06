/* ----------------------------------------------------------------------------------------------
Route map and address suggestions.

Loaded only by the two pages that need them: the order form, where an address box offers places to
pick from, and the order page, where the stored route is drawn. Both talk to this project rather
than to the routing service, so its key stays on the server.
---------------------------------------------------------------------------------------------- */

(function () {
    'use strict';

    const PLACE_FIELD_ATTRIBUTE = 'data-place-field';
    const SUGGESTIONS_URL_ATTRIBUTE = 'data-suggestions-url';
    const SUGGESTION_LIST_CLASS = 'place-suggestions';
    const SUGGESTION_ITEM_CLASS = 'place-suggestion';
    const SUGGESTION_BUSY_CLASS = 'place-suggestions-busy';
    const MINIMUM_QUERY_LENGTH = 3;
    const TYPING_PAUSE_MILLISECONDS = 200;
    const SEARCHING_LABEL = 'Searching…';

    const MAP_SELECTOR = '[data-route-map]';
    const ROUTE_POINTS_ID = 'route-points';
    const ROUTE_DIRECT_ATTRIBUTE = 'data-route-direct';

    const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
    const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    const TILE_MAX_ZOOM = 18;

    const ROUTE_COLOUR = '#0b4fd8';
    const ROUTE_WEIGHT = 4;
    const ROUTE_DASH = '6 8';
    const MAP_PADDING = [28, 28];
    const SINGLE_POINT_ZOOM = 11;

    function debounce(work, delay) {
        let timer = null;
        return function () {
            const context = this;
            const args = arguments;
            window.clearTimeout(timer);
            timer = window.setTimeout(function () { work.apply(context, args); }, delay);
        };
    }

    function initPlaceSuggestions() {
        const form = document.querySelector('[' + SUGGESTIONS_URL_ATTRIBUTE + ']');
        if (!form) {
            return;
        }

        const suggestionsUrl = form.getAttribute(SUGGESTIONS_URL_ATTRIBUTE);

        // The geocoder takes about a second, so a repeated search is answered from here.
        const answered = {};

        Array.prototype.forEach.call(form.querySelectorAll('[' + PLACE_FIELD_ATTRIBUTE + ']'), function (input) {
            const place = input.getAttribute(PLACE_FIELD_ATTRIBUTE);
            const latitude = form.querySelector('[name="' + place + '_latitude"]');
            const longitude = form.querySelector('[name="' + place + '_longitude"]');
            let latestRequest = 0;

            const list = document.createElement('ul');
            list.className = SUGGESTION_LIST_CLASS;
            list.hidden = true;
            input.parentNode.appendChild(list);

            // Taking the press keeps focus in the box, so the list still stands when the click lands.
            list.addEventListener('mousedown', function (event) {
                event.preventDefault();
            });

            function clearCoordinates() {
                latitude.value = '';
                longitude.value = '';
            }

            function hide() {
                list.hidden = true;
                list.innerHTML = '';
                list.classList.remove(SUGGESTION_BUSY_CLASS);
            }

            function showSearching() {
                const item = document.createElement('li');

                item.textContent = SEARCHING_LABEL;
                list.innerHTML = '';
                list.appendChild(item);
                list.classList.add(SUGGESTION_BUSY_CLASS);
                list.hidden = false;
            }

            function show(places) {
                list.innerHTML = '';
                list.classList.remove(SUGGESTION_BUSY_CLASS);

                places.forEach(function (place) {
                    const item = document.createElement('li');
                    const button = document.createElement('button');

                    button.type = 'button';
                    button.className = SUGGESTION_ITEM_CLASS;
                    button.textContent = place.label;
                    button.addEventListener('click', function () {
                        input.value = place.label;
                        latitude.value = place.latitude;
                        longitude.value = place.longitude;
                        hide();
                    });

                    item.appendChild(button);
                    list.appendChild(item);
                });

                list.hidden = places.length === 0;
            }

            const lookUp = debounce(function () {
                const text = input.value.trim();

                if (text.length < MINIMUM_QUERY_LENGTH) {
                    hide();
                    return;
                }

                if (answered[text]) {
                    show(answered[text]);
                    return;
                }

                // Each search is numbered, so a slow earlier answer cannot replace the current list.
                latestRequest += 1;
                const request = latestRequest;

                showSearching();

                window.fetch(suggestionsUrl + '?q=' + encodeURIComponent(text), { credentials: 'same-origin' })
                    .then(function (response) { return response.ok ? response.json() : { places: [] }; })
                    .then(function (data) {
                        answered[text] = data.places;

                        if (request === latestRequest) {
                            show(data.places);
                        }
                    })
                    .catch(function () {
                        if (request === latestRequest) {
                            hide();
                        }
                    });
            }, TYPING_PAUSE_MILLISECONDS);

            // Typing again drops the pick, so coordinates never belong to a different address.
            input.addEventListener('input', function () {
                clearCoordinates();
                lookUp();
            });

            // Pressing inside the list is taken above, so a blur here is a genuine move away from the box.
            input.addEventListener('blur', hide);
        });
    }

    function initRouteMap() {
        const container = document.querySelector(MAP_SELECTOR);

        if (!container || !window.L) {
            return;
        }

        const data = document.getElementById(ROUTE_POINTS_ID);
        if (!data) {
            return;
        }

        const points = JSON.parse(data.textContent);
        if (points.length === 0) {
            return;
        }

        const map = window.L.map(container, { scrollWheelZoom: false });
        window.L.tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION, maxZoom: TILE_MAX_ZOOM }).addTo(map);

        const options = { color: ROUTE_COLOUR, weight: ROUTE_WEIGHT };
        // A direct line is an estimate rather than a surveyed path, and is drawn dashed to say so.
        if (container.hasAttribute(ROUTE_DIRECT_ATTRIBUTE)) {
            options.dashArray = ROUTE_DASH;
        }

        const line = window.L.polyline(points, options).addTo(map);
        window.L.marker(points[0]).addTo(map);
        window.L.marker(points[points.length - 1]).addTo(map);

        if (points.length === 1) {
            map.setView(points[0], SINGLE_POINT_ZOOM);
        } else {
            map.fitBounds(line.getBounds(), { padding: MAP_PADDING });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initPlaceSuggestions();
        initRouteMap();
    });
}());
