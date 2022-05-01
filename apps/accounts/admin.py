"""Admin registration and layout for the account model."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account


@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_admin', 'is_staff', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('is_admin', 'is_staff', 'is_superuser', 'is_verified', 'is_active')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'mobile', 'city', 'country')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    # The model has no groups or permissions relations for the default widget to target.
    filter_horizontal = ()

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'gender', 'date_of_birth', 'profile_image')}),
        ('Contact', {'fields': ('mobile', 'house_number', 'address_line', 'city', 'postal_code', 'country')}),
        ('Social', {'fields': ('linkedin_url', 'facebook_url', 'twitter_url')}),
        ('Permissions', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_admin', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
