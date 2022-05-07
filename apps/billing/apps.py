"""Application configuration for the billing app."""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    name = 'apps.billing'

    def ready(self):
        """Connect the receiver that opens a payment against every new order."""

        from . import signals
