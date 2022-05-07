"""Views for settling an order, keeping a card for the next one, and drawing an invoice."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from apps.transport.models import TransportOrder

from .forms import PaymentForm
from .models import Payment, PaymentStatus, SavedCard, build_receipt_reference
from .responses import invoice_response

PAYMENT_TEMPLATE = 'billing/payment.html'
INVOICE_TEMPLATE = 'billing/invoice.html'
CARD_LIST_TEMPLATE = 'billing/saved-cards.html'

PAYMENT_TAKEN_MESSAGE = 'Order {reference} is paid. Your receipt number is {receipt}.'
CARD_SAVED_MESSAGE = 'Your {label} has been saved for next time.'
CARD_REMOVED_MESSAGE = 'Your {label} has been removed.'
ORDER_NOT_PAYABLE_MESSAGE = 'Order {reference} cannot be paid: it is {status}.'
NO_INVOICE_MESSAGE = 'Order {reference} has no invoice yet, because it has not been paid.'


class OwnOrderMixin(LoginRequiredMixin):
    """Finds an order among the signed-in account's own, so another's is a 404 rather than a refusal.

    A refusal would confirm that the order exists, which is exactly what the number was guessed for.
    """

    def get_order(self):
        return get_object_or_404(TransportOrder, pk=self.kwargs['pk'], account=self.request.user)


class PaymentView(OwnOrderMixin, FormView):
    """Settles one order by card, and keeps the card when asked to."""

    form_class = PaymentForm
    template_name = PAYMENT_TEMPLATE

    def dispatch(self, request, *args, **kwargs):
        """Turn away an order that has nothing left to settle, before a form is built for it."""

        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        self.order = self.get_order()
        if not self.order.can_be_paid:
            reason = 'already paid' if self.order.is_paid else self.order.get_status_display().lower()
            messages.error(request, ORDER_NOT_PAYABLE_MESSAGE.format(reference=self.order.reference, status=reason))
            return redirect('order_detail', pk=self.order.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'cards': SavedCard.objects.filter(account=self.request.user)}

    def get_context_data(self, **kwargs):
        return super().get_context_data(order=self.order, **kwargs)

    def get_success_url(self):
        return reverse('invoice', args=[self.order.pk])

    def form_valid(self, form):
        """Record the payment, and keep the card's description when the payer asked for that."""

        details = form.card_details()
        receipt = build_receipt_reference(self.order)

        # The order already carries a payment, so settling fills it in, with a fresh receipt each time.
        Payment.objects.update_or_create(
            order=self.order,
            defaults={
                'account': self.request.user,
                'amount': self.order.cost,
                'status': PaymentStatus.PAID,
                'reference': receipt,
                'card_brand': details['brand'],
                'card_last_four': details['last_four'],
                'paid_at': timezone.now(),
            },
        )

        kept = form.keep_card_for(self.request.user)
        messages.success(self.request, PAYMENT_TAKEN_MESSAGE.format(reference=self.order.reference, receipt=receipt))

        if kept:
            messages.info(self.request, CARD_SAVED_MESSAGE.format(label=kept.label))

        return super().form_valid(form)


class InvoiceMixin(OwnOrderMixin):
    """Finds an order that has an invoice to show, and sends the rest back where they came from."""

    def get_invoiced_order(self, request):
        order = self.get_order()
        if not order.has_invoice:
            messages.error(request, NO_INVOICE_MESSAGE.format(reference=order.reference))
            return None

        return order


class InvoiceView(InvoiceMixin, TemplateView):
    """Shows the invoice as a page, with the file itself a button away."""

    template_name = INVOICE_TEMPLATE

    def get(self, request, pk):
        order = self.get_invoiced_order(request)
        if order is None:
            return redirect('order_detail', pk=pk)

        return self.render_to_response(self.get_context_data(
            order=order,
            payment=order.payment_record,
            back_url=reverse('order_detail', args=[order.pk]),
            download_url=reverse('invoice_download', args=[order.pk]),
        ))


class InvoiceDownloadView(InvoiceMixin, View):
    """Hands over the invoice as a PDF file, drawn on the way out rather than stored."""

    def get(self, request, pk):
        order = self.get_invoiced_order(request)
        if order is None:
            return redirect('order_detail', pk=pk)

        return invoice_response(order)


class SavedCardListView(LoginRequiredMixin, ListView):
    """Lists the cards this account keeps, so one can be recognised and removed."""

    template_name = CARD_LIST_TEMPLATE
    context_object_name = 'cards'

    def get_queryset(self):
        return SavedCard.objects.filter(account=self.request.user)


class SavedCardDeleteView(LoginRequiredMixin, View):
    """Removes one kept card. POST only, and only from among this account's own."""

    def post(self, request, pk):
        card = get_object_or_404(SavedCard, pk=pk, account=request.user)
        label = card.label
        card.delete()

        messages.success(request, CARD_REMOVED_MESSAGE.format(label=label))
        return redirect('saved_cards')
