"""One-time token generators for the links emailed to account owners."""

from django.contrib.auth.tokens import PasswordResetTokenGenerator

ACTIVATION_KEY_SALT = 'apps.accounts.tokens.AccountActivationTokenGenerator'
EMAIL_CHANGE_KEY_SALT = 'apps.accounts.tokens.EmailChangeTokenGenerator'


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """Signs activation links so that verifying an address consumes the link that carried it.

    A distinct salt keeps reset tokens out, and folding `is_verified` in retires the link on use.
    """

    key_salt = ACTIVATION_KEY_SALT

    def _make_hash_value(self, user, timestamp):
        return f'{super()._make_hash_value(user, timestamp)}{user.is_verified}'


class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    """Signs the link that confirms an account's new email address.

    Folding the pending address in retires an earlier link, and clearing it on confirmation stops reuse.
    """

    key_salt = EMAIL_CHANGE_KEY_SALT

    def _make_hash_value(self, user, timestamp):
        return f'{super()._make_hash_value(user, timestamp)}{user.pending_email}'


account_activation_token = AccountActivationTokenGenerator()
email_change_token = EmailChangeTokenGenerator()
