"""URL routes for registration, authentication, password management and the profile.

The password route names are Django's own, reversed internally between reset steps, so they stand.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import ChangePasswordForm, PasswordResetRequestForm, SetNewPasswordForm

PASSWORD_CHANGE_TEMPLATE = 'accounts/password-change.html'
PASSWORD_CHANGE_DONE_TEMPLATE = 'accounts/password-change-done.html'
PASSWORD_RESET_TEMPLATE = 'accounts/password-reset.html'
PASSWORD_RESET_SENT_TEMPLATE = 'accounts/password-reset-sent.html'
PASSWORD_RESET_CONFIRM_TEMPLATE = 'accounts/password-reset-confirm.html'
PASSWORD_RESET_COMPLETE_TEMPLATE = 'accounts/password-reset-complete.html'
PASSWORD_RESET_EMAIL_TEMPLATE = 'accounts/password-reset-email.html'
PASSWORD_RESET_SUBJECT_TEMPLATE = 'accounts/password-reset-subject.txt'

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('signin/', views.SignInView.as_view(), name='signin'),
    path('signout/', views.SignOutView.as_view(), name='signout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path(
        'password-change/',
        views.PasswordChangeView.as_view(form_class=ChangePasswordForm, template_name=PASSWORD_CHANGE_TEMPLATE),
        name='password_change',
    ),
    path(
        'password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(template_name=PASSWORD_CHANGE_DONE_TEMPLATE),
        name='password_change_done',
    ),
    path(
        'password-reset/',
        views.PasswordResetView.as_view(
            form_class=PasswordResetRequestForm,
            template_name=PASSWORD_RESET_TEMPLATE,
            email_template_name=PASSWORD_RESET_EMAIL_TEMPLATE,
            subject_template_name=PASSWORD_RESET_SUBJECT_TEMPLATE,
        ),
        name='password_reset',
    ),
    path(
        'password-reset/sent/',
        auth_views.PasswordResetDoneView.as_view(template_name=PASSWORD_RESET_SENT_TEMPLATE, extra_context=views.LINK_LIFETIME_CONTEXT),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        views.PasswordResetConfirmView.as_view(
            form_class=SetNewPasswordForm,
            template_name=PASSWORD_RESET_CONFIRM_TEMPLATE,
            extra_context=views.LINK_LIFETIME_CONTEXT,
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name=PASSWORD_RESET_COMPLETE_TEMPLATE),
        name='password_reset_complete',
    ),
]
