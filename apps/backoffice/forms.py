"""Forms for managing accounts and pricing orders from the back office."""

from django import forms

from apps.accounts.forms import ProfileForm, RegistrationForm
from apps.accounts.models import FLAG_LABELS, SUPERUSER_MANAGED_FLAGS
from apps.common.forms import BootstrapFormMixin
from apps.transport.models import MINIMUM_ORDER_COST, TransportOrder, money_label

# The widest set of flags, declared once and narrowed per account rather than assembled each time.
MANAGEABLE_FLAGS = SUPERUSER_MANAGED_FLAGS

STAFF_ACCESS_LABEL = 'Give this account staff access'

COST_LABEL = 'What this order costs'
COST_REASON_LABEL = 'Why it differs from the quote'
COST_REASON_HELP = 'The account holder is shown this beside the new price, so write it for them to read.'
COST_TOO_LOW_MESSAGE = 'An order cannot cost less than {minimum}.'

COST_ATTRIBUTES = {'inputmode': 'numeric', 'min': MINIMUM_ORDER_COST, 'step': 1}
COST_REASON_ATTRIBUTES = {'placeholder': 'Oversize surcharge agreed with the shipper'}


class AccountCreationForm(RegistrationForm):
    """Creates an account on an administrator's behalf, optionally as staff.

    An administrator vouches for the address, so the account is verified outright and no link is sent.
    """

    class Meta(RegistrationForm.Meta):
        fields = (*RegistrationForm.Meta.fields, 'is_staff')
        labels = {'is_staff': STAFF_ACCESS_LABEL}

    def save(self, commit=True):
        account = super().save(commit=False)
        account.is_verified = True

        if commit:
            account.save()

        return account


class OrderCostForm(BootstrapFormMixin, forms.ModelForm):
    """Prices one order by hand, which only holds for as long as the reason for it is recorded.

    A recorded reason is what keeps a hand-set price, so the form insists on one: without it the next
    save of the order undoes the correction.
    """

    class Meta:
        model = TransportOrder
        fields = ('cost', 'cost_reason')
        labels = {'cost': COST_LABEL, 'cost_reason': COST_REASON_LABEL}
        help_texts = {'cost_reason': COST_REASON_HELP}
        widgets = {
            'cost': forms.NumberInput(attrs=COST_ATTRIBUTES),
            'cost_reason': forms.TextInput(attrs=COST_REASON_ATTRIBUTES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cost_reason'].required = True

    def clean_cost(self):
        """Hold a hand-set price to the same floor a quoted one is held to."""

        cost = self.cleaned_data['cost']

        if cost < MINIMUM_ORDER_COST:
            raise forms.ValidationError(COST_TOO_LOW_MESSAGE.format(minimum=money_label(MINIMUM_ORDER_COST)))

        return cost


class AccountUpdateForm(ProfileForm):
    """Corrects an account's details, and sets the flags the signed-in account may set on it.

    Address, username and password are absent by design: each has its own flow that confirms the
    change with the holder. A flag the actor may not set is removed from the form rather than hidden,
    since `construct_instance` copies only fields that reach `cleaned_data`.
    """

    class Meta(ProfileForm.Meta):
        fields = (*ProfileForm.Meta.fields, *MANAGEABLE_FLAGS)
        labels = {**ProfileForm.Meta.labels, **FLAG_LABELS}

    def __init__(self, *args, manageable_flags=(), **kwargs):
        super().__init__(*args, **kwargs)

        for name in MANAGEABLE_FLAGS:
            if name not in manageable_flags:
                del self.fields[name]

    @property
    def flag_fields(self):
        """Return the permission fields, which the template groups apart from the personal ones."""

        return [self[name] for name in MANAGEABLE_FLAGS if name in self.fields]
