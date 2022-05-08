"""Views for the back office: the dashboard, and the tables the site is managed from.

Staff work orders and enquiries; an administrator also manages accounts, so those pages guard tighter.
"""

import math

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from apps.accounts.models import (
    ADMINISTRATOR_ROLE,
    FLAG_LABELS,
    MEMBER_ROLE,
    STAFF_ROLE,
    SUPERUSER_MANAGED_FLAGS,
    SUPERUSER_ROLE,
)
from apps.billing.models import REVERSIBLE_STATUSES, Payment, PaymentStatus, SavedCard
from apps.billing.responses import invoice_response
from apps.common.lists import FilterGroup, RecordListView
from apps.enquiries.models import ContactEnquiry, EnquiryStatus
from apps.transport.models import MODE_ICONS, OrderStatus, TransportMode, TransportOrder, money_label

from .forms import AccountCreationForm, AccountUpdateForm, OrderCostForm

Account = get_user_model()

DASHBOARD_TEMPLATE = 'backoffice/dashboard.html'
ACCOUNT_LIST_TEMPLATE = 'backoffice/accounts.html'
ACCOUNT_DETAIL_TEMPLATE = 'backoffice/account-detail.html'
ACCOUNT_FORM_TEMPLATE = 'backoffice/account-form.html'
ORDER_LIST_TEMPLATE = 'backoffice/orders.html'
ORDER_DETAIL_TEMPLATE = 'backoffice/order-detail.html'
ENQUIRY_LIST_TEMPLATE = 'backoffice/enquiries.html'
INVOICE_TEMPLATE = 'billing/invoice.html'
PAYMENT_LIST_TEMPLATE = 'backoffice/payments.html'

ACCOUNT_CREATED_MESSAGE = 'Account {username} has been created.'
ACCOUNT_UPDATED_MESSAGE = 'Account {username} has been updated.'
ACCOUNT_DELETED_MESSAGE = 'Account {username} has been deleted, along with the orders it placed.'
ACCOUNT_PROTECTED_MESSAGE = 'You may not act on that account.'
ORDER_STATUS_MESSAGE = 'Order {reference} is now {status}.'
ORDER_DELETED_MESSAGE = 'Order {reference} has been deleted.'
ENQUIRY_DELETED_MESSAGE = 'The enquiry from {name} has been deleted.'
ENQUIRY_STATUS_MESSAGE = 'The enquiry from {name} is now marked {status}.'
ORDER_COST_MESSAGE = 'Order {reference} now costs {cost}, and that is what is payable on it.'
ORDER_PAID_MESSAGE = 'Order {reference} has been paid for, so its cost is fixed. Reverse the payment to change it.'
PAYMENT_STATUS_MESSAGE = 'The payment for order {order} is now marked {status}. It can be paid again.'
PAYMENT_NOT_SETTLED_MESSAGE = 'Payment {reference} was never settled, so there is nothing to reverse.'
UNKNOWN_STATUS_MESSAGE = 'That is not a status this record can be given.'
UNPAID_ORDER_MESSAGE = 'Order {reference} cannot be marked {status} until it has been paid for.'
NO_INVOICE_MESSAGE = 'Order {reference} has no invoice yet, because it has not been paid.'

# The only two a payment may be moved to by hand; being paid is something that happens to it.
REVERSIBLE_STATUS_VALUES = tuple(status.value for status in REVERSIBLE_STATUSES)

# A rank is a combination of flags, written once here rather than re-derived wherever it is needed.
ROLE_FILTERS = (
    (MEMBER_ROLE, Q(is_staff=False, is_admin=False, is_superuser=False)),
    (STAFF_ROLE, Q(is_staff=True, is_admin=False, is_superuser=False)),
    (ADMINISTRATOR_ROLE, Q(is_admin=True, is_superuser=False)),
    (SUPERUSER_ROLE, Q(is_superuser=True)),
)


def redirect_back(request, fallback):
    """Return to the table an action was triggered from, or to `fallback` when that is not safe.

    The form names its page, so an action returns to that search, and an address is followed only if local.
    """

    destination = request.POST.get('next')
    if destination and url_has_allowed_host_and_scheme(destination, {request.get_host()}, request.is_secure()):
        return redirect(destination)

    return redirect(fallback)


def whole_shares(counts):
    """Return each count's share of the total as whole percentages that come to exactly 100.

    Rounding each share alone leaves the bar short — three equal parts give 33% each — so the points
    lost are handed back to the counts cut hardest and the slices fill it exactly.
    """

    total = sum(counts)
    if not total:
        return [0] * len(counts)

    exact = [count * 100 / total for count in counts]
    shares = [math.floor(share) for share in exact]
    spare = 100 - sum(shares)

    for index in sorted(range(len(counts)), key=lambda position: exact[position] - shares[position], reverse=True)[:spare]:
        shares[index] += 1

    return shares


def role_breakdown():
    """Return how many accounts hold each rank, with each one's share of the total."""

    counts = [Account.objects.filter(matches).count() for _, matches in ROLE_FILTERS]

    return [
        {
            'label': label,
            'value': label.lower(),
            'count': count,
            'share': share,
        }
        for (label, _), count, share in zip(ROLE_FILTERS, counts, whole_shares(counts))
    ]


def status_breakdown(model, choices):
    """Return how many of a model's records stand at each status, with each one's share."""

    counts = [model.objects.filter(status=status).count() for status in choices]

    return [
        {
            'label': status.label,
            'value': status.value,
            'count': count,
            'share': share,
        }
        for status, count, share in zip(choices, counts, whole_shares(counts))
    ]


def mode_breakdown():
    """Return how many orders travel by each mode, how many of them are completed, and each one's share."""

    counts = [TransportOrder.objects.filter(mode=mode).count() for mode in TransportMode]
    completed = [TransportOrder.objects.filter(mode=mode, status=OrderStatus.COMPLETED).count() for mode in TransportMode]

    return [
        {
            'label': mode.label,
            'value': mode.value,
            'icon': MODE_ICONS[mode],
            'count': count,
            'completed': done,
            'share': share,
        }
        for mode, count, done, share in zip(TransportMode, counts, completed, whole_shares(counts))
    ]


class BackofficeAccessMixin(UserPassesTestMixin):
    """Restricts a page to the accounts allowed inside the back office at all.

    Signed out is sent to sign in and signed in without the privilege is refused, and the account is
    read only once known to exist, so an anonymous visitor cannot raise `Account.DoesNotExist`.
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_open_backoffice

    def get_context_data(self, **kwargs):
        """Tell the shared navigation which sections this viewer may open.

        Only the pages that render reach this; the actions answer POST and return a redirect.
        """

        return super().get_context_data(may_administer=self.request.user.can_administer_backoffice, **kwargs)


class BackofficeAdministratorMixin(BackofficeAccessMixin):
    """Narrows a page to administrators, who alone may remove a record or act on an account."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_administer_backoffice


class DashboardView(BackofficeAccessMixin, TemplateView):
    """Opens the back office with where the site's records stand, in the sections the viewer may open."""

    template_name = DASHBOARD_TEMPLATE

    def get_context_data(self, **kwargs):
        user = self.request.user

        return super().get_context_data(
            roles=role_breakdown() if user.can_administer_backoffice else None,
            account_total=Account.objects.count() if user.can_administer_backoffice else None,
            order_modes=mode_breakdown(),
            order_statuses=status_breakdown(TransportOrder, OrderStatus),
            order_total=TransportOrder.objects.count(),
            enquiry_statuses=status_breakdown(ContactEnquiry, EnquiryStatus),
            enquiry_total=ContactEnquiry.objects.count(),
            payment_statuses=status_breakdown(Payment, PaymentStatus),
            payment_total=Payment.objects.count(),
            payment_taken=money_label(Payment.objects.filter(status=PaymentStatus.PAID).aggregate(total=Sum('amount'))['total'] or 0),
            accounts_url=reverse('backoffice:accounts'),
            orders_url=reverse('backoffice:orders'),
            enquiries_url=reverse('backoffice:enquiries'),
            payments_url=reverse('backoffice:payments'),
            **kwargs,
        )


class AccountListView(BackofficeAdministratorMixin, RecordListView):
    """Lists every account. Each row opens the account itself, where anything about it is settled."""

    template_name = ACCOUNT_LIST_TEMPLATE
    context_object_name = 'accounts'
    queryset = Account.objects.all()

    search_fields = ('username', 'email', 'first_name', 'last_name')
    search_placeholder = 'Search by name, username or email'
    filter_groups = (FilterGroup('role', 'All roles', tuple((label.lower(), label, matches) for label, matches in ROLE_FILTERS)),)
    sort_options = (
        ('newest', 'Newest first', ('-date_joined',)),
        ('oldest', 'Oldest first', ('date_joined',)),
        ('username', 'Username A to Z', ('username',)),
        ('email', 'Email A to Z', ('email',)),
    )


class AccountDetailView(BackofficeAdministratorMixin, UpdateView):
    """Shows one account in full, and settles whatever the signed-in account may settle about it."""

    model = Account
    form_class = AccountUpdateForm
    template_name = ACCOUNT_DETAIL_TEMPLATE
    context_object_name = 'account'

    def manageable_flags(self):
        return self.request.user.manageable_flags_for(self.object)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'manageable_flags': self.manageable_flags()}

    def get_success_url(self):
        return reverse('backoffice:account_detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        """Add the delete permission, the flags read back when none may be set, and the cards on file.

        The cards are read only: removing one is the holder's to do, from their own payment methods.
        """

        account_flags = [(FLAG_LABELS[name], getattr(self.object, name)) for name in SUPERUSER_MANAGED_FLAGS]

        return super().get_context_data(may_delete=self.request.user.may_delete(self.object),
                                        account_flags=account_flags,
                                        saved_cards=SavedCard.objects.filter(account=self.object),
                                        **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, ACCOUNT_UPDATED_MESSAGE.format(username=self.object.username))
        return response


class AccountCreateView(BackofficeAdministratorMixin, CreateView):
    """Registers an account on an administrator's behalf."""

    form_class = AccountCreationForm
    template_name = ACCOUNT_FORM_TEMPLATE
    success_url = reverse_lazy('backoffice:accounts')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, ACCOUNT_CREATED_MESSAGE.format(username=self.object.username))
        return response


class OrderListView(BackofficeAccessMixin, RecordListView):
    """Lists every order placed, whoever placed it, with its status open to change."""

    template_name = ORDER_LIST_TEMPLATE
    context_object_name = 'orders'
    queryset = TransportOrder.objects.all()
    extra_context = {'statuses': OrderStatus.choices}

    search_fields = ('origin', 'destination', 'account__username', 'account__email', 'payment__reference')
    search_placeholder = 'Search by place or account'
    filter_groups = (
        FilterGroup('status', 'All statuses', tuple((status.value, status.label, Q(status=status.value)) for status in OrderStatus)),
        FilterGroup('mode', 'All modes', tuple((mode.value, mode.label, Q(mode=mode.value)) for mode in TransportMode)),
    )
    sort_options = (
        ('newest', 'Newest first', ('-placed_at',)),
        ('oldest', 'Oldest first', ('placed_at',)),
        ('dearest', 'Cost, highest first', ('-cost',)),
        ('cheapest', 'Cost, lowest first', ('cost',)),
        ('heaviest', 'Weight, heaviest first', ('-weight_kilograms',)),
    )


class OrderDetailView(BackofficeAccessMixin, DetailView):
    """Shows any order in full, whoever placed it, with the actions an administrator may take on it.

    The owner's own page is scoped to their orders; this one is not, which is the whole point of it.
    """

    model = TransportOrder
    template_name = ORDER_DETAIL_TEMPLATE
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        """Offer only the statuses this order may actually be moved to, and the payment beside them."""

        return super().get_context_data(
            statuses=[(value, label) for value, label in OrderStatus.choices if self.object.may_reach(value)],
            payment_statuses=REVERSIBLE_STATUSES,
            payment=self.object.payment_record,
            cost_form=OrderCostForm(instance=self.object),
            **kwargs,
        )


class EnquiryListView(BackofficeAccessMixin, RecordListView):
    """Lists every message sent through the contact page, with how far each has been dealt with."""

    template_name = ENQUIRY_LIST_TEMPLATE
    context_object_name = 'enquiries'
    queryset = ContactEnquiry.objects.all()
    extra_context = {'statuses': EnquiryStatus.choices}

    search_fields = ('name', 'email', 'subject', 'message')
    search_placeholder = 'Search by sender, subject or message'
    filter_groups = (FilterGroup('status', 'All statuses', tuple((status.value, status.label, Q(status=status.value)) for status in EnquiryStatus)),)
    sort_options = (
        ('newest', 'Newest first', ('-submitted_at',)),
        ('oldest', 'Oldest first', ('submitted_at',)),
        ('sender', 'Sender A to Z', ('name',)),
    )


class PaymentListView(BackofficeAccessMixin, RecordListView):
    """Lists every payment taken, whoever made it, and whether it still stands."""

    template_name = PAYMENT_LIST_TEMPLATE
    context_object_name = 'payments'
    queryset = Payment.objects.all()

    search_fields = ('reference', 'account__username', 'account__email', 'card_last_four')
    search_placeholder = 'Search by receipt, account or last four digits'
    filter_groups = (FilterGroup('status', 'All payments', tuple((status.value, status.label, Q(status=status.value)) for status in PaymentStatus)),)
    sort_options = (
        ('newest', 'Newest first', ('-paid_at',)),
        ('oldest', 'Oldest first', ('paid_at',)),
        ('largest', 'Amount, highest first', ('-amount',)),
        ('smallest', 'Amount, lowest first', ('amount',)),
    )


class OrderInvoiceMixin(BackofficeAccessMixin):
    """Finds any order that has an invoice, whoever placed it."""

    def get_invoiced_order(self, request, pk):
        order = get_object_or_404(TransportOrder, pk=pk)
        if not order.has_invoice:
            messages.error(request, NO_INVOICE_MESSAGE.format(reference=order.reference))
            return None

        return order


class OrderInvoiceView(OrderInvoiceMixin, TemplateView):
    """Shows any order's invoice as a page, with the file a button away."""

    template_name = INVOICE_TEMPLATE

    def get(self, request, pk):
        order = self.get_invoiced_order(request, pk)
        if order is None:
            return redirect('backoffice:order_detail', pk=pk)

        return self.render_to_response(self.get_context_data(
            order=order,
            payment=order.payment_record,
            back_url=reverse('backoffice:order_detail', args=[order.pk]),
            download_url=reverse('backoffice:order_invoice_download', args=[order.pk]),
        ))


class OrderInvoiceDownloadView(OrderInvoiceMixin, View):
    """Hands over any order's invoice as a PDF, whoever placed it."""

    def get(self, request, pk):
        order = self.get_invoiced_order(request, pk)
        if order is None:
            return redirect('backoffice:order_detail', pk=pk)

        return invoice_response(order)


class OrderCostUpdateView(BackofficeAccessMixin, View):
    """Prices one order by hand. POST only, and only while there is still something to pay.

    What is owed follows the new figure, so checkout asks the corrected price, not the rate card's.
    """

    def post(self, request, pk):
        order = get_object_or_404(TransportOrder, pk=pk)
        if not order.can_be_repriced:
            messages.error(request, ORDER_PAID_MESSAGE.format(reference=order.reference))
            return redirect('backoffice:order_detail', pk=order.pk)

        form = OrderCostForm(request.POST, instance=order)
        if not form.is_valid():
            for field_errors in form.errors.values():
                messages.error(request, field_errors[0])

            return redirect('backoffice:order_detail', pk=order.pk)

        order = form.save()

        # A payment is opened with every order, but one removed by hand leaves the order without it.
        payment = order.payment_record
        if payment:
            payment.match_order_cost()

        messages.success(request, ORDER_COST_MESSAGE.format(reference=order.reference, cost=order.cost_label))
        return redirect('backoffice:order_detail', pk=order.pk)


class PaymentStatusUpdateView(BackofficeAdministratorMixin, View):
    """Marks where an order's payment stands. POST only, and an administrator's alone.

    Only the two ways a payment stops standing: an order is marked paid by being paid for.
    """

    def post(self, request, pk):
        payment = get_object_or_404(Payment, order__pk=pk)
        status = request.POST.get('status')

        if status not in REVERSIBLE_STATUS_VALUES:
            messages.error(request, UNKNOWN_STATUS_MESSAGE)
            return redirect_back(request, 'backoffice:orders')
        if not payment.is_settled:
            messages.error(request, PAYMENT_NOT_SETTLED_MESSAGE.format(reference=payment.reference))
            return redirect_back(request, 'backoffice:orders')

        payment.status = status
        payment.save(update_fields=['status', 'updated_at'])

        reached = PaymentStatus(status).label.lower()
        messages.success(request, PAYMENT_STATUS_MESSAGE.format(order=payment.order.reference, status=reached))
        return redirect_back(request, 'backoffice:orders')


class AccountDeleteView(BackofficeAdministratorMixin, View):
    """Deletes an account and everything that belongs to it. POST only.

    The same rule as setting a flag: no peer an administrator cannot demote, and never oneself.
    """

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)

        if not request.user.may_delete(account):
            messages.error(request, ACCOUNT_PROTECTED_MESSAGE)
            return redirect_back(request, 'backoffice:accounts')

        username = account.username
        account.delete()
        messages.success(request, ACCOUNT_DELETED_MESSAGE.format(username=username))
        return redirect('backoffice:accounts')


class OrderStatusUpdateView(BackofficeAccessMixin, View):
    """Moves an order to the status chosen for it. POST only."""

    def post(self, request, pk):
        order = get_object_or_404(TransportOrder, pk=pk)
        status = request.POST.get('status')

        if status not in OrderStatus.values:
            messages.error(request, UNKNOWN_STATUS_MESSAGE)
            return redirect_back(request, 'backoffice:orders')
        # Freight is not handed over before it is paid for, and withholding the option is presentation.
        if not order.may_reach(status):
            messages.error(request, UNPAID_ORDER_MESSAGE.format(reference=order.reference, status=OrderStatus(status).label.lower()))
            return redirect_back(request, 'backoffice:orders')

        order.status = status
        order.save(update_fields=['status'])

        reached = OrderStatus(status).label.lower()
        messages.success(request, ORDER_STATUS_MESSAGE.format(reference=order.reference, status=reached))
        return redirect_back(request, 'backoffice:orders')


class EnquiryStatusUpdateView(BackofficeAccessMixin, View):
    """Marks how far an enquiry has been dealt with. POST only."""

    def post(self, request, pk):
        enquiry = get_object_or_404(ContactEnquiry, pk=pk)
        status = request.POST.get('status')

        if status not in EnquiryStatus.values:
            messages.error(request, UNKNOWN_STATUS_MESSAGE)
            return redirect_back(request, 'backoffice:enquiries')

        enquiry.status = status
        enquiry.save(update_fields=['status'])

        reached = EnquiryStatus(status).label.lower()
        messages.success(request, ENQUIRY_STATUS_MESSAGE.format(name=enquiry.name, status=reached))
        return redirect_back(request, 'backoffice:enquiries')


class OrderDeleteView(BackofficeAdministratorMixin, View):
    """Deletes an order outright, for one placed in error. POST only."""

    def post(self, request, pk):
        order = get_object_or_404(TransportOrder, pk=pk)
        reference = order.reference
        order.delete()

        messages.success(request, ORDER_DELETED_MESSAGE.format(reference=reference))
        return redirect_back(request, 'backoffice:orders')


class EnquiryDeleteView(BackofficeAdministratorMixin, View):
    """Deletes a contact enquiry once it has been dealt with. POST only."""

    def post(self, request, pk):
        enquiry = get_object_or_404(ContactEnquiry, pk=pk)
        name = enquiry.name
        enquiry.delete()

        messages.success(request, ENQUIRY_DELETED_MESSAGE.format(name=name))
        return redirect_back(request, 'backoffice:enquiries')
