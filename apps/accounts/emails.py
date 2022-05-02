"""Transactional email sent by the account flows."""

import logging
import threading

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import account_activation_token

ACTIVATION_SUBJECT = 'Verify your CTMS email address'
ACTIVATION_TEMPLATE = 'accounts/activation-email.html'

PASSWORD_CHANGED_SUBJECT = 'Your CTMS password was changed'
PASSWORD_CHANGED_TEMPLATE = 'accounts/password-changed-email.html'

logger = logging.getLogger(__name__)


class EmailThread(threading.Thread):
    """Delivers one message off the request thread, so a slow mail server cannot stall a response."""

    def __init__(self, message):
        self.message = message
        super().__init__(daemon=True)

    def run(self):
        try:
            self.message.send()
        except Exception:
            # An unhandled exception in a thread leaves no trace, so delivery errors are recorded.
            logger.exception('Unable to send "%s" to %s', self.message.subject, ', '.join(self.message.to))


def send_account_email(subject, template_name, user, request, recipient=None, **extra_context):
    """Render a plain-text body for the account owner and hand the message to a delivery thread.

    Links are absolute, so the request's scheme and host go into the context with the link lifetime.
    A recipient may be named for the one message that goes to an address the account has left.
    """

    context = {
        'user': user,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': get_current_site(request).domain,
        'link_lifetime_minutes': settings.ACCOUNT_LINK_LIFETIME_MINUTES,
        **extra_context,
    }
    message = EmailMessage(subject=subject, body=render_to_string(template_name, context), to=[recipient or user.email])
    EmailThread(message).start()


def send_activation_email(user, request):
    """Email the account owner the link that verifies their address."""

    send_account_email(
        ACTIVATION_SUBJECT, ACTIVATION_TEMPLATE, user, request,
        uidb64=urlsafe_base64_encode(force_bytes(user.pk)),
        token=account_activation_token.make_token(user),
    )


def send_password_changed_email(user, request):
    """Tell the account owner their password was replaced, so a change they did not make is noticed."""

    send_account_email(PASSWORD_CHANGED_SUBJECT, PASSWORD_CHANGED_TEMPLATE, user, request)
