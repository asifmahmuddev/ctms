"""Form for the public contact page."""

from django import forms

from apps.common.forms import BootstrapFormMixin
from apps.common.recaptcha import RecaptchaFormMixin

from .models import ContactEnquiry

ENQUIRY_FIELDS = ('name', 'email', 'phone', 'subject', 'message')

MESSAGE_ROWS = 6
MINIMUM_MESSAGE_LENGTH = 10
SHORT_MESSAGE = 'Please describe your enquiry in at least {length} characters.'


class ContactEnquiryForm(RecaptchaFormMixin, BootstrapFormMixin, forms.ModelForm):
    """Collects a message from a visitor, who need not hold an account to send one."""

    class Meta:
        model = ContactEnquiry
        fields = ENQUIRY_FIELDS
        labels = {'phone': 'Phone (optional)'}
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel'}),
            'message': forms.Textarea(attrs={'rows': MESSAGE_ROWS}),
        }

    def clean_message(self):
        """Refuse a message too short to act on, which the field's own length limit cannot catch."""

        message = self.cleaned_data['message'].strip()
        if len(message) < MINIMUM_MESSAGE_LENGTH:
            raise forms.ValidationError(SHORT_MESSAGE.format(length=MINIMUM_MESSAGE_LENGTH), code='message_too_short')

        return message
