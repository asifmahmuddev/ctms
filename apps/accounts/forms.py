"""Forms for registration, authentication, password management and the profile."""

import datetime
from urllib.parse import urlsplit

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm, UserCreationForm, UsernameField
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.formats import date_format

from apps.common.forms import BootstrapFormMixin
from apps.common.recaptcha import RecaptchaFormMixin

from .models import MAX_LENGTH_EMAIL, MAX_LENGTH_URL, MAX_LENGTH_USERNAME

Account = get_user_model()

# The model leaves both blank for admin-created accounts; registration asks, as orders need a name.
REQUIRED_REGISTRATION_FIELDS = ('first_name', 'last_name')

# Django's wording warns both fields may be case-sensitive; the backend ignores address case.
INVALID_CREDENTIALS_MESSAGE = 'Please enter a correct email address and password. The password is case-sensitive.'
UNVERIFIED_EMAIL_MESSAGE = 'This email address has not been verified yet. We have emailed you a new verification link.'
UNKNOWN_EMAIL_MESSAGE = 'No active account is registered with that email address.'
UNCHANGED_PASSWORD_MESSAGE = 'Your new password must be different from your current password.'
EMAIL_TAKEN_MESSAGE = 'Another account already uses that email address.'
UNCHANGED_EMAIL_MESSAGE = 'That is already your email address.'
USERNAME_TAKEN_MESSAGE = 'Another account already uses that username.'
WRONG_PASSWORD_MESSAGE = 'That is not your current password.'
OVERSIZED_IMAGE_MESSAGE = 'Choose a picture smaller than {limit} MB.'
UNSUPPORTED_IMAGE_MESSAGE = 'Choose a PNG or JPEG picture.'
EARLY_BIRTH_DATE_MESSAGE = 'Your date of birth cannot be before {year}.'
LATE_BIRTH_DATE_MESSAGE = 'Your date of birth cannot be after {date}.'

GENDER_CHOICES = (
    ('', 'Prefer not to say'),
    ('Female', 'Female'),
    ('Male', 'Male'),
    ('Other', 'Other'),
)

# The groups every editor shows, so the holder's page and the administrator's share one definition.
PROFILE_FIELD_GROUPS = (
    ('Personal details', 'fa-id-card', ('first_name', 'last_name', 'gender', 'date_of_birth')),
    ('Contact', 'fa-address-book', ('mobile', 'house_number', 'address_line', 'city', 'postal_code', 'country')),
    ('Social links', 'fa-share-alt', ('facebook_url', 'instagram_url', 'twitter_url', 'linkedin_url')),
)

PROFILE_FIELDS = tuple(name for _, _, names in PROFILE_FIELD_GROUPS for name in names)

# The browser's date control only understands this format, and refuses to show anything else.
DATE_INPUT_FORMAT = '%Y-%m-%d'

SECURE_SCHEME = 'https'

EARLIEST_BIRTH_DATE = datetime.date(1900, 1, 1)

# How far back the newest allowed date of birth sits, keeping today and every later day out.
MINIMUM_AGE_YEARS = 1

MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024
BYTES_PER_MEGABYTE = 1024 * 1024

# Formats a browser can crop and hand back; a phone's multi-picture JPEG reads as MPO, not JPEG.
ALLOWED_IMAGE_FORMATS = ('PNG', 'JPEG', 'MPO')
ACCEPTED_IMAGE_TYPES = 'image/png, image/jpeg'


class SecureUrlField(forms.URLField):
    """A URL field that reads a missing scheme as https rather than as the http Django assumes.

    `URLField.to_python` fills in `http` when it finds no scheme, with no setting to change it, so
    supplying https first leaves that branch nothing to do and a typed scheme is still kept.
    """

    def to_python(self, value):
        if value and not urlsplit(value).scheme:
            value = f'{SECURE_SCHEME}://{value}'

        return super().to_python(value)


def latest_birth_date():
    """Return the newest date of birth an account may hold, a whole minimum age before today.

    Counting in calendar years rather than days keeps the boundary on the same day of the month.
    """

    today = timezone.localdate()
    try:
        return today.replace(year=today.year - MINIMUM_AGE_YEARS)
    except ValueError:
        # 29 February has no counterpart in a common year, so the last day of that February stands in.
        return today.replace(day=28, year=today.year - MINIMUM_AGE_YEARS)


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


class SignUpForm(RecaptchaFormMixin, RegistrationForm):
    """Registration as the public page offers it, weighed by reCAPTCHA before an account is made."""


class SignInForm(RecaptchaFormMixin, BootstrapFormMixin, AuthenticationForm):
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


class PasswordResetRequestForm(RecaptchaFormMixin, BootstrapFormMixin, PasswordResetForm):
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


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Edits the details an account holder can change without confirming anything.

    Bound to the signed-in account, so fields render pre-filled and a cleared one stays cleared.
    """

    facebook_url = SecureUrlField(max_length=MAX_LENGTH_URL, required=False, label='Facebook')
    instagram_url = SecureUrlField(max_length=MAX_LENGTH_URL, required=False, label='Instagram')
    twitter_url = SecureUrlField(max_length=MAX_LENGTH_URL, required=False, label='Twitter')
    linkedin_url = SecureUrlField(max_length=MAX_LENGTH_URL, required=False, label='LinkedIn')

    class Meta:
        model = Account
        fields = PROFILE_FIELDS
        labels = {'address_line': 'Address'}
        widgets = {
            'gender': forms.Select(choices=GENDER_CHOICES),
            'date_of_birth': forms.DateInput(format=DATE_INPUT_FORMAT, attrs={'type': 'date'}),
            'mobile': forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set per render rather than declared on the widget, because the last allowed day moves.
        date_of_birth_attrs = self.fields['date_of_birth'].widget.attrs
        date_of_birth_attrs['min'] = EARLIEST_BIRTH_DATE.isoformat()
        date_of_birth_attrs['max'] = latest_birth_date().isoformat()

    @property
    def field_groups(self):
        """Return the profile fields grouped as they are shown, skipping any group left out of a form."""

        groups = []
        for title, icon, names in PROFILE_FIELD_GROUPS:
            fields = [self[name] for name in names if name in self.fields]
            if fields:
                groups.append({'title': title, 'icon': icon, 'fields': fields})

        return groups

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data['date_of_birth']
        if date_of_birth:
            latest = latest_birth_date()
            if date_of_birth > latest:
                raise ValidationError(LATE_BIRTH_DATE_MESSAGE.format(date=date_format(latest)), code='date_too_late')
            if date_of_birth < EARLIEST_BIRTH_DATE:
                raise ValidationError(EARLY_BIRTH_DATE_MESSAGE.format(year=EARLIEST_BIRTH_DATE.year), code='date_too_early')

        return date_of_birth


class ProfileImageForm(forms.Form):
    """Carries a new profile picture and the square the account holder selected from it."""

    image = forms.ImageField(widget=forms.ClearableFileInput(attrs={
        'class': 'visually-hidden',
        'accept': ACCEPTED_IMAGE_TYPES,
        'data-max-bytes': MAX_PROFILE_IMAGE_BYTES,
    }))
    crop_x = forms.IntegerField(required=False, widget=forms.HiddenInput)
    crop_y = forms.IntegerField(required=False, widget=forms.HiddenInput)
    crop_width = forms.IntegerField(required=False, widget=forms.HiddenInput)
    crop_height = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def clean_image(self):
        """Accept only a format the browser can display, within a size no setting caps for file data.

        The format is read from the file's own bytes, so renaming a picture cannot smuggle it past.
        """

        image = self.cleaned_data['image']
        if image.image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(UNSUPPORTED_IMAGE_MESSAGE, code='unsupported_image')
        if image.size > MAX_PROFILE_IMAGE_BYTES:
            limit = MAX_PROFILE_IMAGE_BYTES // BYTES_PER_MEGABYTE
            raise ValidationError(OVERSIZED_IMAGE_MESSAGE.format(limit=limit), code='image_too_large')

        return image

    def selection(self):
        """Return the selected square, or None when the browser sent no selection to work from."""

        corners = [self.cleaned_data.get(name) for name in ('crop_x', 'crop_y', 'crop_width', 'crop_height')]
        return tuple(corners) if all(corner is not None for corner in corners) else None


class CredentialChangeForm(BootstrapFormMixin, forms.Form):
    """Base for the forms that change how an account is identified, guarded by its current password.

    Plain forms rather than model forms, because nothing is written here: the address is only
    confirmed and the username is saved by its view. The password is declared first, so each form
    names its own field order to put the value being changed above the password that authorises it.
    """

    current_password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data['current_password']
        if not self.user.check_password(current_password):
            raise ValidationError(WRONG_PASSWORD_MESSAGE, code='wrong_password')

        return current_password


class EmailChangeForm(CredentialChangeForm):
    """Collects the address an account wants to move to."""

    field_order = ('email', 'current_password')

    email = forms.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        label='New email address',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if email == self.user.email:
            raise ValidationError(UNCHANGED_EMAIL_MESSAGE, code='email_unchanged')
        if Account.objects.email_is_taken(email, self.user.pk):
            raise ValidationError(EMAIL_TAKEN_MESSAGE, code='email_taken')

        return email


class UsernameChangeForm(CredentialChangeForm):
    """Renames an account, leaving its own current name available to keep."""

    field_order = ('username', 'current_password')

    username = UsernameField(max_length=MAX_LENGTH_USERNAME, label='New username')

    def clean_username(self):
        username = self.cleaned_data['username']
        if Account.objects.filter(username__iexact=username).exclude(pk=self.user.pk).exists():
            raise ValidationError(USERNAME_TAKEN_MESSAGE, code='username_taken')

        return username
