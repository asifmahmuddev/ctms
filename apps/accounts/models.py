"""Account model, its manager, and the upload location for profile images."""

import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

MAX_LENGTH_NAME = 32
MAX_LENGTH_USERNAME = 64
MAX_LENGTH_PHONE = 64
MAX_LENGTH_EMAIL = 128
MAX_LENGTH_ADDRESS = 128
MAX_LENGTH_POSTAL_CODE = 32
MAX_LENGTH_URL = 255
MAX_LENGTH_IMAGE_PATH = 255

PROFILE_IMAGE_DIR = 'profile-images'
DEFAULT_PROFILE_IMAGE = f'{PROFILE_IMAGE_DIR}/default.png'

# The two columns describing a requested address change are always written and cleared together.
PENDING_EMAIL_FIELDS = ('pending_email', 'pending_email_requested_at')
PENDING_EMAIL_LIFETIME = datetime.timedelta(minutes=settings.ACCOUNT_LINK_LIFETIME_MINUTES)


def profile_image_path(instance, _filename):
    """Return the upload path for an account's profile image.

    One image per account in its own directory under a stable name; Django passes the old one positionally.
    """

    return f'{PROFILE_IMAGE_DIR}/{instance.pk}/{instance.pk}-profile.png'


class AccountManager(BaseUserManager):
    """Creates accounts with a normalised email address and a hashed password."""

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')

        user = self.model(
            email=self.normalize_email(email).lower(),
            username=username,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(email, username, password, **extra_fields)

    def email_is_taken(self, email, exclude_pk):
        """Return whether an account other than the given one already holds this email address."""

        return self.filter(email__iexact=email).exclude(pk=exclude_pk).exists()


class Account(AbstractBaseUser):
    """A registered user, identified by email address."""

    # `password` and `last_login` are inherited from AbstractBaseUser.
    date_joined = models.DateTimeField(auto_now_add=True)

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    username = models.CharField(max_length=MAX_LENGTH_USERNAME, unique=True)
    email = models.EmailField(max_length=MAX_LENGTH_EMAIL, unique=True)

    # Held until the link sent to it is opened, and not unique: the first to confirm gets it.
    pending_email = models.EmailField(max_length=MAX_LENGTH_EMAIL, blank=True, null=True)
    pending_email_requested_at = models.DateTimeField(blank=True, null=True)

    profile_image = models.ImageField(
        max_length=MAX_LENGTH_IMAGE_PATH,
        upload_to=profile_image_path,
        default=DEFAULT_PROFILE_IMAGE,
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=MAX_LENGTH_NAME, blank=True, null=True)
    last_name = models.CharField(max_length=MAX_LENGTH_NAME, blank=True, null=True)
    gender = models.CharField(max_length=MAX_LENGTH_NAME, blank=True, null=True)
    date_of_birth = models.DateField(default=None, blank=True, null=True)

    mobile = models.CharField(max_length=MAX_LENGTH_PHONE, blank=True, null=True)
    house_number = models.CharField(max_length=MAX_LENGTH_ADDRESS, blank=True, null=True)
    address_line = models.CharField(max_length=MAX_LENGTH_ADDRESS, blank=True, null=True)
    city = models.CharField(max_length=MAX_LENGTH_ADDRESS, blank=True, null=True)
    postal_code = models.CharField(max_length=MAX_LENGTH_POSTAL_CODE, blank=True, null=True)
    country = models.CharField(max_length=MAX_LENGTH_ADDRESS, blank=True, null=True)

    facebook_url = models.CharField(max_length=MAX_LENGTH_URL, blank=True, null=True)
    instagram_url = models.CharField(max_length=MAX_LENGTH_URL, blank=True, null=True)
    twitter_url = models.CharField(max_length=MAX_LENGTH_URL, blank=True, null=True)
    linkedin_url = models.CharField(max_length=MAX_LENGTH_URL, blank=True, null=True)

    objects = AccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username

    def get_full_name(self):
        """Return the account's full name, falling back to the username when no name is set."""

        parts = [part for part in (self.first_name, self.last_name) if part]
        return ' '.join(parts) if parts else self.username

    def get_short_name(self):
        return self.first_name or self.username

    @property
    def email_change_is_pending(self):
        """Return whether a requested address is still waiting for a link that can still be opened.

        Measured over the lifetime the link's token is signed against, so both lapse at one moment.
        """

        if not self.pending_email or not self.pending_email_requested_at:
            return False

        return timezone.now() - self.pending_email_requested_at < PENDING_EMAIL_LIFETIME

    def forget_lapsed_email_change(self):
        """Drop a requested address whose link has lapsed, so no address outlives the request for it.

        A mistyped address belongs to somebody else, and holding an unconfirmable one gains nothing.
        """

        if self.pending_email and not self.email_change_is_pending:
            self.pending_email = None
            self.pending_email_requested_at = None
            self.save(update_fields=PENDING_EMAIL_FIELDS)

    @property
    def profile_image_url(self):
        """Return the picture's address, falling back to the shared default when the file is missing.

        A stored path outlives its file when media is cleared, so the file itself is checked.
        """

        picture = self.profile_image
        if picture and picture.storage.exists(picture.name):
            return picture.url

        return picture.storage.url(DEFAULT_PROFILE_IMAGE)

    # Administrators hold every permission; with no per-object rules the arguments are unused.
    def has_perm(self, _perm, _obj=None):
        return self.is_admin

    def has_module_perms(self, _app_label):
        return self.is_admin
