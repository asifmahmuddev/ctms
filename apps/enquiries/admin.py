"""Admin registration and layout for contact enquiries."""

from django.contrib import admin

from .models import ContactEnquiry


@admin.register(ContactEnquiry)
class ContactEnquiryAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'phone', 'status', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'subject', 'message')
    ordering = ('-submitted_at',)

    # An enquiry records what a visitor sent, so only how far it has been dealt with may be edited.
    readonly_fields = ('submitted_at', 'name', 'email', 'phone', 'subject', 'message')

    def has_add_permission(self, request):
        return False
