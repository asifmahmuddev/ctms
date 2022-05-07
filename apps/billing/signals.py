"""Gives every order a payment of its own the moment it is placed.

An unpaid order still has a payment status, so no table carries a column that is sometimes blank.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.transport.models import TransportOrder

from .models import Payment, build_receipt_reference


@receiver(post_save, sender=TransportOrder, dispatch_uid='billing.open_payment_for_order')
def open_payment_for_order(sender, instance, created, **kwargs):
    """Open a payment against a newly placed order, owing its full cost.

    Django hands the sender and the keyword arguments to every receiver whether it reads them or not.
    """

    if not created:
        return

    Payment.objects.create(
        order=instance,
        account=instance.account,
        amount=instance.cost,
        reference=build_receipt_reference(instance),
    )
