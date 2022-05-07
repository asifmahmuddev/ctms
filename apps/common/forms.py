"""Form furniture shared by every app, so no app reaches into another for its styling."""

from django import forms

CONTROL_CLASS = 'form-control'
SELECT_CLASS = 'form-select'
CHECK_CLASS = 'form-check-input'

# The icon each field wears, held here rather than in templates so it renders the same everywhere.
DEFAULT_FIELD_ICON = 'fa-pen'

FIELD_ICONS = {
    # Identity
    'first_name': 'fa-user',
    'last_name': 'fa-user',
    'username': 'fa-signature',
    'email': 'fa-at',
    'gender': 'fa-venus-mars',
    'date_of_birth': 'fa-birthday-cake',
    'image': 'fa-camera',

    # Credentials
    'password': 'fa-key',
    'password1': 'fa-key',
    'password2': 'fa-key',
    'new_password1': 'fa-key',
    'new_password2': 'fa-key',
    'old_password': 'fa-unlock-alt',
    'current_password': 'fa-unlock-alt',
    'remember_me': 'fa-clock',

    # Contact and address
    'mobile': 'fa-mobile-alt',
    'phone': 'fa-phone',
    'house_number': 'fa-hashtag',
    'address_line': 'fa-map-marker-alt',
    'city': 'fa-city',
    'postal_code': 'fa-mail-bulk',
    'country': 'fa-globe',

    # Social links
    'facebook_url': 'fa-facebook-f',
    'instagram_url': 'fa-instagram',
    'twitter_url': 'fa-twitter',
    'linkedin_url': 'fa-linkedin-in',

    # Enquiries
    'name': 'fa-user',
    'subject': 'fa-tag',
    'message': 'fa-comment-dots',

    # Orders
    'mode': 'fa-route',
    'origin': 'fa-plane-departure',
    'destination': 'fa-plane-arrival',
    'weight_kilograms': 'fa-weight-hanging',
    'cost': 'fa-dollar-sign',

    # Payment
    'card_number': 'fa-credit-card',
    'cardholder_name': 'fa-user',
    'expiry': 'fa-calendar-alt',
    'security_code': 'fa-lock',
    'save_card': 'fa-bookmark',
    'saved_card': 'fa-credit-card',

    # Permissions
    'is_admin': 'fa-user-shield',
    'is_staff': 'fa-user-tie',
    'is_verified': 'fa-check-circle',
    'is_active': 'fa-toggle-on',
}

# Brands whose mark belongs to the brand family rather than the solid one.
BRAND_ICONS = {'fa-facebook-f', 'fa-instagram', 'fa-twitter', 'fa-linkedin-in'}


def control_class_for(widget):
    """Return the Bootstrap class that styles this kind of control."""

    if isinstance(widget, forms.CheckboxInput):
        return CHECK_CLASS
    if isinstance(widget, forms.Select):
        return SELECT_CLASS

    return CONTROL_CLASS


def icon_for(field_name):
    """Return the icon a field wears, as the Font Awesome family and name a template can render."""

    icon = FIELD_ICONS.get(field_name, DEFAULT_FIELD_ICON)
    return f'{"fab" if icon in BRAND_ICONS else "fas"} {icon}'


class BootstrapFormMixin:
    """Applies Bootstrap control classes and a label icon to every field.

    A class already on a widget wins, and the icon rides the field so a template only reads it.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.icon = icon_for(name)

            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault('class', control_class_for(field.widget))
