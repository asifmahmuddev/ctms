"""The checkout form.

The card number and security code are validated then discarded, never stored. What survives is what
recognises the card again — its brand, last four digits, expiry and the name on it.
"""

import re

from django import forms
from django.utils import timezone

from apps.common.forms import BootstrapFormMixin

from .models import LAST_FOUR_DIGITS, SavedCard

# Card numbers are 12 to 19 digits, typed with whatever spacing the card is printed in.
CARD_NUMBER_PATTERN = re.compile(r'^\d{12,19}$')
NON_DIGITS = re.compile(r'\D')
SECURITY_CODE_PATTERN = re.compile(r'^\d{3,4}$')
EXPIRY_PATTERN = re.compile(r'^(0[1-9]|1[0-2])\s*/\s*(\d{2})$')

# The first digits say which network issued a card, which is all that is kept of the number itself.
CARD_BRANDS = (
    (re.compile(r'^4'), 'Visa'),
    (re.compile(r'^(5[1-5]|2[2-7])'), 'Mastercard'),
    (re.compile(r'^3[47]'), 'American Express'),
    (re.compile(r'^6(011|5)'), 'Discover'),
)
UNKNOWN_BRAND = 'Card'

CENTURY = 2000

NEW_CARD_CHOICE = ''
NEW_CARD_LABEL = 'Use a new card'

# A choice label is escaped on the way out, so the wording carries no markup of its own.
SAVED_CARD_CHOICE_LABEL = '{label}, expires {expiry}'

CARD_NUMBER_MESSAGE = 'Enter a card number of 12 to 19 digits.'
SECURITY_CODE_MESSAGE = 'Enter the 3 or 4 digit security code from the back of the card.'
EXPIRY_MESSAGE = 'Enter the expiry as MM/YY, exactly as it is printed on the card.'
CARDHOLDER_MESSAGE = 'Enter the name printed on the card.'
EXPIRED_MESSAGE = 'That card expired in {label}. Use one that is still valid.'
SAVED_CARD_EXPIRED_MESSAGE = 'That saved card has expired. Pay with a new one and it will replace it.'

# What each control tells the browser about itself, so a phone offers its own card filler.
NUMBER_ATTRIBUTES = {'inputmode': 'numeric', 'autocomplete': 'cc-number', 'placeholder': '4242 4242 4242 4242'}
NAME_ATTRIBUTES = {'autocomplete': 'cc-name'}
EXPIRY_ATTRIBUTES = {'inputmode': 'numeric', 'autocomplete': 'cc-exp', 'placeholder': 'MM/YY', 'maxlength': '5'}
SECURITY_CODE_ATTRIBUTES = {'inputmode': 'numeric', 'autocomplete': 'cc-csc', 'placeholder': '123'}

# Rendered as a password so a shoulder cannot read the code, and never sent back to the page.
SECURITY_CODE_WIDGET = forms.PasswordInput(render_value=False, attrs=SECURITY_CODE_ATTRIBUTES)


def brand_for(number):
    """Return the network a card number belongs to, or a neutral word when none of them claims it."""

    for pattern, brand in CARD_BRANDS:
        if pattern.match(number):
            return brand

    return UNKNOWN_BRAND


class PaymentForm(BootstrapFormMixin, forms.Form):
    """Takes a card, checks it is well formed and unexpired, and keeps only what identifies it."""

    saved_card = forms.ChoiceField(required=False, label='Pay with')
    card_number = forms.CharField(required=False, label='Card number', widget=forms.TextInput(attrs=NUMBER_ATTRIBUTES))
    cardholder_name = forms.CharField(required=False, label='Name on card', widget=forms.TextInput(attrs=NAME_ATTRIBUTES))
    expiry = forms.CharField(required=False, label='Expiry', widget=forms.TextInput(attrs=EXPIRY_ATTRIBUTES))
    security_code = forms.CharField(required=False, label='Security code', widget=SECURITY_CODE_WIDGET)
    save_card = forms.BooleanField(required=False, label='Save this card for next time')

    def __init__(self, *args, cards=(), **kwargs):
        super().__init__(*args, **kwargs)

        self.cards = {str(card.pk): card for card in cards}

        # A new card leads, since the form below is filled in for it; a kept one turns those off.
        kept = [
            (str(card.pk), SAVED_CARD_CHOICE_LABEL.format(label=card.label, expiry=card.expiry_label))
            for card in cards
        ]
        self.fields['saved_card'].choices = [(NEW_CARD_CHOICE, NEW_CARD_LABEL), *kept]

        if not self.cards:
            del self.fields['saved_card']

    @property
    def chosen_card(self):
        """Return the kept card being paid with, or None when the details were typed out."""

        return self.cards.get(self.cleaned_data.get('saved_card', NEW_CARD_CHOICE))

    def clean_card_number(self):
        """Return the digits of the number, having dropped whatever spacing it was typed with."""

        return NON_DIGITS.sub('', self.cleaned_data['card_number'])

    def clean_security_code(self):
        return self.cleaned_data['security_code'].strip()

    def clean_expiry(self):
        return self.cleaned_data['expiry'].strip()

    def clean(self):
        """Check the details the chosen way of paying actually needs.

        A kept card needs only its security code; a new one needs all four, checked here rather than
        field by field so choosing a kept card does not report four as missing.
        """

        cleaned_data = super().clean()
        card = self.chosen_card

        # The pattern refuses an empty code as readily as a malformed one, so both read the same way.
        if not SECURITY_CODE_PATTERN.match(cleaned_data.get('security_code', '')):
            self.add_error('security_code', SECURITY_CODE_MESSAGE)
        if card:
            if card.has_expired:
                self.add_error('saved_card', SAVED_CARD_EXPIRED_MESSAGE)

            return cleaned_data
        if not CARD_NUMBER_PATTERN.match(cleaned_data.get('card_number', '')):
            self.add_error('card_number', CARD_NUMBER_MESSAGE)
        if not cleaned_data.get('cardholder_name', '').strip():
            self.add_error('cardholder_name', CARDHOLDER_MESSAGE)

        self.clean_new_card_expiry(cleaned_data)
        return cleaned_data

    def clean_new_card_expiry(self, cleaned_data):
        """Check a typed expiry is a real month that has not already passed."""

        match = EXPIRY_PATTERN.match(cleaned_data.get('expiry', ''))
        if not match:
            self.add_error('expiry', EXPIRY_MESSAGE)
            return

        month, year = int(match.group(1)), CENTURY + int(match.group(2))
        today = timezone.localdate()
        if (year, month) < (today.year, today.month):
            self.add_error('expiry', EXPIRED_MESSAGE.format(label=f'{month:02d}/{year % 100:02d}'))
            return

        cleaned_data['expiry_month'] = month
        cleaned_data['expiry_year'] = year

    def card_details(self):
        """Return what is kept of the card being paid with: never the number, never the code."""

        card = self.chosen_card
        if card:
            return {'brand': card.brand, 'last_four': card.last_four,
                    'expiry_month': card.expiry_month, 'expiry_year': card.expiry_year,
                    'cardholder_name': card.cardholder_name}

        number = self.cleaned_data['card_number']
        return {
            'brand': brand_for(number),
            'last_four': number[-LAST_FOUR_DIGITS:],
            'expiry_month': self.cleaned_data['expiry_month'],
            'expiry_year': self.cleaned_data['expiry_year'],
            'cardholder_name': self.cleaned_data['cardholder_name'].strip(),
        }

    def keep_card_for(self, account):
        """Store the card's description against the account, unless it is one already on file.

        Recognised by brand and last four digits, so paying twice with one leaves a single row.
        """

        if self.chosen_card or not self.cleaned_data.get('save_card'):
            return None

        details = self.card_details()
        card, _ = SavedCard.objects.update_or_create(account=account, brand=details['brand'], last_four=details['last_four'], defaults=details)
        return card
