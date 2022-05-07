"""Admin registration for payments and the cards accounts keep."""

from django.contrib import admin

from .models import Payment, SavedCard


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'order', 'account', 'amount', 'status', 'card_brand', 'card_last_four', 'paid_at')
    list_filter = ('status', 'card_brand')
    search_fields = ('reference', 'account__email', 'card_last_four')

    # A payment records what happened; correcting it would rewrite history rather than describe it.
    readonly_fields = ('order', 'account', 'amount', 'reference', 'card_brand', 'card_last_four', 'paid_at')


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = ('account', 'brand', 'last_four', 'expiry_month', 'expiry_year', 'added_at')
    list_filter = ('brand',)
    search_fields = ('account__email', 'last_four')

    # A kept card is the account holder's own record; nobody else edits what it says.
    readonly_fields = ('account', 'brand', 'last_four', 'expiry_month', 'expiry_year', 'cardholder_name', 'added_at')
