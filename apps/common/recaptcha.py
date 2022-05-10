"""Scoring of reCAPTCHA tokens, and the form mixin that carries one and acts on the verdict."""

import logging

import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

# The browser mints a token into this field, which is why the name is repeated in the site script.
TOKEN_FIELD_NAME = 'recaptcha_token'

REFUSED_MESSAGE = 'We could not confirm that this was submitted by a person. Please try again.'

logger = logging.getLogger(__name__)


def submission_scores_as_human(token):
    """Return whether the service scores this token at or above the configured line.

    Two cases pass unscored: no secret key, so the project runs without an account at the service,
    and a service that cannot be reached, which must not take the site down with it.
    """

    if not settings.RECAPTCHA_SECRET_KEY:
        return True
    if not token:
        return False

    try:
        response = requests.post(
            VERIFY_URL,
            data={'secret': settings.RECAPTCHA_SECRET_KEY, 'response': token},
            timeout=settings.RECAPTCHA_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        verdict = response.json()
    except (requests.RequestException, ValueError):
        logger.exception('Could not reach the reCAPTCHA service; the submission was allowed through')
        return True

    if not verdict.get('success'):
        logger.info('reCAPTCHA refused a token: %s', verdict.get('error-codes'))
        return False

    score = verdict.get('score')
    if score is None:
        logger.error('reCAPTCHA returned no score, which a key registered for the checkbox version never does')
        return False

    return score >= settings.RECAPTCHA_MINIMUM_SCORE


class RecaptchaFormMixin:
    """Carries a reCAPTCHA token and refuses the submission when the service scores it too low.

    Weighed before anything else the form checks, so a refusal never reaches the rest of the work.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[TOKEN_FIELD_NAME] = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean(self):
        if not submission_scores_as_human(self.data.get(TOKEN_FIELD_NAME)):
            raise ValidationError(REFUSED_MESSAGE, code='recaptcha_refused')

        return super().clean()
