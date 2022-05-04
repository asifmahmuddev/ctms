"""View for the public contact page."""

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .forms import ContactEnquiryForm
from .models import MAX_LENGTH_SUBJECT

CONTACT_TEMPLATE = 'enquiries/contact.html'

# A page that sends somebody here for a particular reason names it in the query string.
SUBJECT_PARAMETER = 'subject'

ENQUIRY_SENT_MESSAGE = 'Thank you, your message has been sent. Our support team will reply to {email}.'


class ContactEnquiryCreateView(CreateView):
    """Takes a message from any visitor, signed in or not, and records it for the support team."""

    form_class = ContactEnquiryForm
    template_name = CONTACT_TEMPLATE
    success_url = reverse_lazy('contact')

    def get_initial(self):
        """Fill in what is already known, so a visitor retypes nothing they have told us.

        A subject from the query string is trimmed to the column, so no link presents a doomed form.
        """

        initial = dict(super().get_initial())
        subject = self.request.GET.get(SUBJECT_PARAMETER)
        user = self.request.user

        if subject:
            initial['subject'] = subject[:MAX_LENGTH_SUBJECT]
        if user.is_authenticated:
            initial.update(name=user.get_full_name(), email=user.email, phone=user.mobile)

        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, ENQUIRY_SENT_MESSAGE.format(email=self.object.email))
        return response
