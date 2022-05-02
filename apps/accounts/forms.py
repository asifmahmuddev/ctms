"""Forms for registration, authentication and password management."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm, UserCreationForm, UsernameField
from django.core.exceptions import ValidationError

from apps.common.forms import BootstrapFormMixin

Account = get_user_model()

# The model leaves both blank for admin-created accounts; registration asks, as orders need a name.
REQUIRED_REGISTRATION_FIELDS = ('first_name', 'last_name')

# Django's wording warns both fields may be case-sensitive; the backend ignores address case.
INVALID_CREDENTIALS_MESSAGE = 'Please enter a correct email address and password. The password is case-sensitive.'
UNVERIFIED_EMAIL_MESSAGE = 'This email address has not been verified yet. We have emailed you a new verification link.'
UNKNOWN_EMAIL_MESSAGE = 'No active account is registered with that email address.'
UNCHANGED_PASSWORD_MESSAGE = 'Your new password must be different from your current password.'


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Registers an account, hashing the password and running it through the configured validators."""

    class Meta:
        model = Account
        fields = ('first_name', 'last_name', 'email', 'username')
        field_classes = {'username': UsernameField}
        widgets = {'email': forms.EmailInput(attrs={'autocomplete': 'email'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in REQUIRED_REGISTRATION_FIELDS:
            self.fields[field_name].required = True

    def clean_email(self):
        """Return the address in lower case, so two accounts cannot differ only by capitalisation."""

        return self.cleaned_data['email'].lower()


class SignInForm(BootstrapFormMixin, AuthenticationForm):
    """Authenticates on email address and refuses accounts whose address is still unverified."""

    username = UsernameField(widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'}))
    remember_me = forms.BooleanField(required=False, label='Keep me signed in')

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': INVALID_CREDENTIALS_MESSAGE,
        'unverified': UNVERIFIED_EMAIL_MESSAGE,
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.is_verified:
            raise ValidationError(self.error_messages['unverified'], code='unverified')


class PasswordResetRequestForm(BootstrapFormMixin, PasswordResetForm):
    """Names an unknown address rather than reporting success for one that can never receive a link."""

    def clean_email(self):
        email = self.cleaned_data['email']
        if not Account.objects.filter(email__iexact=email, is_active=True).exists():
            raise ValidationError(UNKNOWN_EMAIL_MESSAGE, code='unknown_email')

        return email


class NewPasswordMixin:
    """Refuses a replacement identical to the password the account already uses.

    Both forms hold the account as `user`, so the check runs against the stored hash on its own.
    """

    def clean_new_password1(self):
        new_password = self.cleaned_data['new_password1']
        if self.user.check_password(new_password):
            raise ValidationError(UNCHANGED_PASSWORD_MESSAGE, code='password_unchanged')

        return new_password


class SetNewPasswordForm(BootstrapFormMixin, NewPasswordMixin, SetPasswordForm):
    """Sets a new password from a reset link, where the old one is unknown by definition."""


class ChangePasswordForm(BootstrapFormMixin, NewPasswordMixin, PasswordChangeForm):
    """Changes the password of a signed-in account, confirming the current one first."""
