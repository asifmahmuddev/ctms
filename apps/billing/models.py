"""Payments taken against an order, and the cards an account keeps for the next one.

No card number and no security code is ever stored. A kept card holds only what recognises it — the
brand, last four digits, expiry and the name on it — never anything that could charge it.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.transport.models import CURRENCY_SYMBOL

MAX_LENGTH_CHOICE = 16
MAX_LENGTH_BRAND = 24
MAX_LENGTH_NAME = 64
MAX_LENGTH_REFERENCE = 32

LAST_FOUR_DIGITS = 4

RECEIPT_PREFIX = 'RCP'
RECEIPT_STAMP_FORMAT = '%y%m%d%H%M%S'

# The stamp alone repeats within a second, so a short random tail keeps each receipt its own.
RECEIPT_TAIL_LENGTH = 4
RECEIPT_TAIL_CHARACTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
INVOICE_PREFIX = 'INV'
DOCUMENT_NUMBER_DIGITS = 6

# What a card is shown as when it is offered again, and how an expiry reads.
CARD_LABEL = '{brand} ending {last_four}'
NO_CARD_LABEL = 'Not paid yet'
EXPIRY_LABEL = '{month:02d}/{year}'


class PaymentStatus(models.TextChoices):
    """Where an order's payment stands, from owing through settled to given back or gone wrong."""

    PENDING = 'payment-pending', 'Payment Pending'
    PAID = 'paid', 'Paid'
    REFUNDED = 'refunded', 'Refunded'
    FAILED = 'failed', 'Failed'


# Only an administrator sets these, and only on a payment that was actually taken.
REVERSIBLE_STATUSES = (PaymentStatus.REFUNDED, PaymentStatus.FAILED)

# What each status wears wherever a payment is shown on its own.
PAYMENT_STATUS_ICONS = {
    PaymentStatus.PENDING: 'fa-hourglass-half',
    PaymentStatus.PAID: 'fa-check-circle',
    PaymentStatus.REFUNDED: 'fa-undo',
    PaymentStatus.FAILED: 'fa-times-circle',
}


class SavedCard(models.Model):
    """A card an account chose to keep, described well enough to recognise and never to charge."""

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_cards')
    added_at = models.DateTimeField(auto_now_add=True)

    brand = models.CharField(max_length=MAX_LENGTH_BRAND)
    last_four = models.CharField(max_length=LAST_FOUR_DIGITS)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    cardholder_name = models.CharField(max_length=MAX_LENGTH_NAME)

    class Meta:
        ordering = ('-added_at',)

    def __str__(self):
        return self.label

    @property
    def label(self):
        return CARD_LABEL.format(brand=self.brand, last_four=self.last_four)

    @property
    def expiry_label(self):
        return EXPIRY_LABEL.format(month=self.expiry_month, year=self.expiry_year % 100)

    @property
    def has_expired(self):
        """Return whether the card's last valid month has passed, since a card outlives its usefulness."""

        today = timezone.localdate()
        return (self.expiry_year, self.expiry_month) < (today.year, today.month)


class Payment(models.Model):
    """What was settled against one order, and how.

    One payment per order: refunding marks this record given back, reopening the order rather than adding a row.
    """

    order = models.OneToOneField('transport.TransportOrder', on_delete=models.CASCADE, related_name='payment')
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')

    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=MAX_LENGTH_CHOICE, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    reference = models.CharField(max_length=MAX_LENGTH_REFERENCE, unique=True)

    # Recognisable on a statement, kept apart from any card later removed, and empty until settled.
    card_brand = models.CharField(max_length=MAX_LENGTH_BRAND, blank=True)
    card_last_four = models.CharField(max_length=LAST_FOUR_DIGITS, blank=True)

    # When it was settled, which an unpaid one never was, and when it last moved either way.
    paid_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        return f'{self.reference} for {self.order.reference}'

    @property
    def amount_label(self):
        return f'{CURRENCY_SYMBOL}{self.amount:,}'

    @property
    def invoice_number(self):
        """Return the number this order's invoice is issued under, which never changes once set."""

        return f'{INVOICE_PREFIX}-{self.order_id:0{DOCUMENT_NUMBER_DIGITS}d}'

    @property
    def card_label(self):
        """Return how the card reads, or a word standing in for one that was never given."""

        if not self.card_brand:
            return NO_CARD_LABEL

        return CARD_LABEL.format(brand=self.card_brand, last_four=self.card_last_four)

    @property
    def status_icon(self):
        return PAYMENT_STATUS_ICONS[PaymentStatus(self.status)]

    @property
    def is_settled(self):
        """Return whether this payment stands, which only a paid one does."""

        return self.status == PaymentStatus.PAID

    @property
    def is_refunded(self):
        return self.status == PaymentStatus.REFUNDED

    @property
    def is_failed(self):
        return self.status == PaymentStatus.FAILED

    @property
    def has_invoice(self):
        """Return whether an invoice can be drawn, which needs the order to have been settled once."""

        return self.paid_at is not None

    def match_order_cost(self):
        """Set what is owed to the order's current cost, which only an unsettled payment may do.

        A settled one keeps the figure its receipt and invoice quote, whatever the order is repriced at.
        """

        if self.is_settled or self.amount == self.order.cost:
            return

        self.amount = self.order.cost
        self.save(update_fields=['amount', 'updated_at'])


def build_receipt_reference(order):
    """Return the receipt number a payment against this order is recorded under.

    The order's number is folded in, so a receipt names its order, and the moment stops reuse after a refund.
    """

    stamp = timezone.now().strftime(RECEIPT_STAMP_FORMAT)
    tail = get_random_string(RECEIPT_TAIL_LENGTH, RECEIPT_TAIL_CHARACTERS)
    return f'{RECEIPT_PREFIX}-{order.pk:0{DOCUMENT_NUMBER_DIGITS}d}-{stamp}-{tail}'
