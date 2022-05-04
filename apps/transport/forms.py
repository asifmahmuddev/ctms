"""Form for placing a transport order."""

from django import forms

from apps.common.forms import BootstrapFormMixin

from .models import MAXIMUM_WEIGHT_KILOGRAMS, MINIMUM_WEIGHT_KILOGRAMS, TransportMode, TransportOrder

ORDER_FIELDS = ('mode', 'origin', 'destination', 'weight_kilograms')

MODE_PROMPT = 'Choose how it travels'
ORIGIN_PLACEHOLDER = 'City and country the cargo leaves from'
DESTINATION_PLACEHOLDER = 'City and country the cargo is bound for'
SAME_PLACE_MESSAGE = 'The destination must differ from the origin.'
WEIGHT_STEP = '0.01'
WEIGHT_HELP_TEXT = f'Kilograms, from {MINIMUM_WEIGHT_KILOGRAMS} up to {MAXIMUM_WEIGHT_KILOGRAMS:,}. Fractions are allowed, as 7.6.'


class TransportOrderForm(BootstrapFormMixin, forms.ModelForm):
    """Collects a consignment to be moved.

    Only the four fields an account decides are offered; cost and status are set on save, so neither
    can be dictated by whoever submits the form. The weight is declared rather than derived, so the
    browser is handed the real floor and a step fine enough for a fractional weight.
    """

    weight_kilograms = forms.FloatField(
        min_value=MINIMUM_WEIGHT_KILOGRAMS,
        max_value=MAXIMUM_WEIGHT_KILOGRAMS,
        label='Total weight',
        help_text=WEIGHT_HELP_TEXT,
        widget=forms.NumberInput(attrs={'step': WEIGHT_STEP}),
    )

    class Meta:
        model = TransportOrder
        fields = ORDER_FIELDS
        labels = {'mode': 'Transport by'}
        widgets = {
            'origin': forms.TextInput(attrs={'placeholder': ORIGIN_PLACEHOLDER, 'autocomplete': 'off'}),
            'destination': forms.TextInput(attrs={'placeholder': DESTINATION_PLACEHOLDER, 'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # A prompt rather than Django's dashes, and empty, so submitting without choosing is refused.
        self.fields['mode'].choices = [('', MODE_PROMPT), *TransportMode.choices]

    def clean(self):
        """Refuse a route that goes nowhere, which the fields cannot rule out on their own."""

        cleaned_data = super().clean()
        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')

        if origin and destination and origin.casefold() == destination.casefold():
            self.add_error('destination', SAME_PLACE_MESSAGE)

        return cleaned_data
