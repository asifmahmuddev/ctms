"""Admin registration and layout for transport orders."""

from django.contrib import admin

from .models import TransportOrder


@admin.register(TransportOrder)
class TransportOrderAdmin(admin.ModelAdmin):
    list_display = ('reference', 'account', 'mode', 'origin', 'destination', 'weight_kilograms', 'cost', 'status', 'placed_at')
    list_filter = ('status', 'mode')
    search_fields = ('origin', 'destination', 'account__email', 'account__username')
    ordering = ('-placed_at',)

    # The model prices every order it saves, so the cost is shown here rather than entered.
    readonly_fields = ('placed_at', 'cost')

    fieldsets = (
        (None, {'fields': ('account', 'status', 'placed_at')}),
        ('Consignment', {'fields': ('mode', 'origin', 'destination', 'weight_kilograms', 'cost')}),
    )
