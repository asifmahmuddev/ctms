"""The organisation this site represents, held once and read wherever it is shown.

Every page and invoice reads this one record rather than a copy, so correcting it corrects the site.
"""

from django.db import models

MAX_LENGTH_NAME = 64
MAX_LENGTH_FULL_NAME = 128
MAX_LENGTH_EMAIL = 254
MAX_LENGTH_PHONE = 32
MAX_LENGTH_ADDRESS = 160
MAX_LENGTH_CITY = 64
MAX_LENGTH_COUNTRY = 64

# One organisation, so one row, always under the same key.
PROFILE_KEY = 1

# What the site reads as until an administrator says otherwise.
DEFAULT_TRADING_NAME = 'CTMS'
DEFAULT_FULL_NAME = 'Cargo Transportation Management System'
DEFAULT_CONTACT_EMAIL = 'asifmahmud.ide@gmail.com'
DEFAULT_PHONE = '+880 123 456 789'
DEFAULT_ADDRESS_LINE = '11 Commercial Area'
DEFAULT_CITY = 'Dhaka'
DEFAULT_COUNTRY = 'Bangladesh'


class CompanyProfile(models.Model):
    """The single record naming the company, its address and how to reach it."""

    trading_name = models.CharField(max_length=MAX_LENGTH_NAME, default=DEFAULT_TRADING_NAME)
    full_name = models.CharField(max_length=MAX_LENGTH_FULL_NAME, default=DEFAULT_FULL_NAME)

    contact_email = models.EmailField(max_length=MAX_LENGTH_EMAIL, default=DEFAULT_CONTACT_EMAIL)
    phone = models.CharField(max_length=MAX_LENGTH_PHONE, default=DEFAULT_PHONE)

    address_line = models.CharField(max_length=MAX_LENGTH_ADDRESS, default=DEFAULT_ADDRESS_LINE)
    city = models.CharField(max_length=MAX_LENGTH_CITY, default=DEFAULT_CITY)
    country = models.CharField(max_length=MAX_LENGTH_COUNTRY, default=DEFAULT_COUNTRY)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.trading_name

    def save(self, *args, **kwargs):
        """Keep the record under its one key, so a second company can never be created by accident."""

        self.pk = PROFILE_KEY
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        """Return the company, creating it from the defaults the first time it is asked for."""

        profile, _ = cls.objects.get_or_create(pk=PROFILE_KEY)
        return profile

    @property
    def location(self):
        """Return where the company sits, as one line, leaving out whichever part is not set."""

        return ', '.join(part for part in (self.city, self.country) if part)

    @property
    def address_lines(self):
        """Return the postal address as the lines an invoice prints it on."""

        return [line for line in (self.address_line, self.location) if line]
