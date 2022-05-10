"""Adapter that ties a Google sign-in to an account of this project."""

import re

from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect

from .models import MAX_LENGTH_USERNAME, Account

# A username is derived from the address: the local part keeps letters and digits, and a `+tag` names the same inbox and is dropped.
ADDRESS_SEPARATOR = '@'
TAG_SEPARATOR = '+'
DISALLOWED_USERNAME_CHARACTERS = re.compile(r'[^a-z0-9]')
FALLBACK_USERNAME = 'member'

# The plain name is offered first; one already held is then tried as `name2`, `name3` and so on.
FIRST_USERNAME_SUFFIX = 2

VERIFIED_FIELD = 'is_verified'
SIGN_IN_URL_NAME = 'signin'
INACTIVE_ACCOUNT_MESSAGE = 'This account has been deactivated. Get in touch if you think that is a mistake.'
MISSING_EMAIL_MESSAGE = 'Google did not share an email address, which an account here is identified by.'


def username_from_email(email):
    """Return the letters and digits of an address's local part, or a fallback when it holds none."""

    local_part = email.partition(ADDRESS_SEPARATOR)[0].partition(TAG_SEPARATOR)[0]
    return DISALLOWED_USERNAME_CHARACTERS.sub('', local_part.lower()) or FALLBACK_USERNAME


def unique_username(email):
    """Return a username no account holds yet, numbering it only once the plain form is taken."""

    base = username_from_email(email)
    candidate = base[:MAX_LENGTH_USERNAME]
    suffix = FIRST_USERNAME_SUFFIX

    # Matched without regard to case, because that is how the account forms judge a name to be taken.
    while Account.objects.filter(username__iexact=candidate).exists():
        number = str(suffix)
        candidate = f'{base[:MAX_LENGTH_USERNAME - len(number)]}{number}'
        suffix += 1

    return candidate


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    """Decides which account a Google sign-in belongs to, and what a new one is created with.

    Google reports only checked addresses, so the account is verified and matched to any existing one.
    """

    def pre_social_login(self, request, sociallogin):
        """Settle which account this sign-in belongs to, before the library considers making one."""

        if not sociallogin.user.email:
            messages.error(request, MISSING_EMAIL_MESSAGE)
            raise ImmediateHttpResponse(redirect(SIGN_IN_URL_NAME))
        if sociallogin.is_existing:
            account = sociallogin.user
        else:
            account = Account.objects.filter(email__iexact=sociallogin.user.email).first()
            if account is None:
                return

        if not account.is_active:
            messages.error(request, INACTIVE_ACCOUNT_MESSAGE)
            raise ImmediateHttpResponse(redirect(SIGN_IN_URL_NAME))
        if not sociallogin.is_existing:
            account.is_verified = True
            # Connecting writes the account, so the flag set above is stored along with the link.
            sociallogin.connect(request, account)
        elif not account.is_verified:
            account.is_verified = True
            account.save(update_fields=[VERIFIED_FIELD])

    def is_auto_signup_allowed(self, request, sociallogin):
        """Always create the account, because which account this is has already been settled above.

        The library would otherwise refuse on a stale row in its own address table, left by an
        address the account has since moved off, and ask the visitor to sign up a second time.
        """

        return True

    def save_user(self, request, sociallogin, form=None):
        """Name and verify a brand-new account before the library writes it.

        A username set here is kept, because the library fills one only when none is found, and the
        password is left unusable, so the reset flow is how one is ever set.
        """

        account = sociallogin.user
        account.username = unique_username(account.email)
        account.is_verified = True
        return super().save_user(request, sociallogin, form)
