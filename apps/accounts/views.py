"""Views for registration, authentication, activation and password management."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView

from .emails import send_activation_email, send_password_changed_email
from .forms import RegistrationForm, SignInForm
from .tokens import account_activation_token

Account = get_user_model()

SIGN_UP_TEMPLATE = 'accounts/signup.html'
SIGN_IN_TEMPLATE = 'accounts/signin.html'
ACTIVATION_FAILED_TEMPLATE = 'accounts/activation-failed.html'

LINK_LIFETIME_MINUTES = settings.ACCOUNT_LINK_LIFETIME_MINUTES

# Every page and message that quotes the deadline reads it from here, so none can drift.
LINK_LIFETIME_CONTEXT = {'link_lifetime_minutes': LINK_LIFETIME_MINUTES}

SIGN_UP_MESSAGE = (
    'Your account has been created. Open the link we emailed you to verify your address, '
    'then sign in.'
)
SIGN_IN_MESSAGE = 'You are now signed in as {email}.'
SIGN_OUT_MESSAGE = 'You have been signed out of your CTMS account.'
ACTIVATION_MESSAGE = 'Email address verified. You can sign in now.'


def account_from_uidb64(uidb64):
    """Return the account a signed link points at, or None when the identifier is unusable."""

    try:
        return Account.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (Account.DoesNotExist, TypeError, ValueError):
        return None


class SignUpView(CreateView):
    """Registers an account and emails its owner the link that verifies their address."""

    form_class = RegistrationForm
    template_name = SIGN_UP_TEMPLATE
    success_url = reverse_lazy('signin')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        send_activation_email(self.object, self.request)
        messages.success(self.request, SIGN_UP_MESSAGE)
        return response


class SignInView(auth_views.LoginView):
    """Signs an account in, and issues a fresh verification link when the address is still unverified."""

    authentication_form = SignInForm
    template_name = SIGN_IN_TEMPLATE
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Logging in cycles the session key, so the lifetime is set on the session that survives it.
        response = super().form_valid(form)
        user = form.get_user()

        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)

        messages.success(self.request, SIGN_IN_MESSAGE.format(email=user.email))
        return response

    def form_invalid(self, form):
        # The form rejects an unverified account only after the password matched, so it is theirs.
        user = form.get_user()
        if user is not None and not user.is_verified:
            send_activation_email(user, self.request)

        return super().form_invalid(form)


@method_decorator(require_POST, name='dispatch')
class SignOutView(auth_views.LogoutView):
    """Ends the session. POST only, so a prefetched link or an image tag cannot sign an account out."""

    def dispatch(self, request, *args, **kwargs):
        was_signed_in = request.user.is_authenticated
        response = super().dispatch(request, *args, **kwargs)

        # Signing out flushes the session the message store writes to, so the message is added after.
        if was_signed_in:
            messages.success(request, SIGN_OUT_MESSAGE)

        return response


class PasswordResetView(auth_views.PasswordResetView):
    """Emails a reset link, telling its recipient how long the link stays valid."""

    extra_email_context = LINK_LIFETIME_CONTEXT


class PasswordChangeView(auth_views.PasswordChangeView):
    """Replaces the password of a signed-in account and tells its owner that it happened."""

    def form_valid(self, form):
        response = super().form_valid(form)
        send_password_changed_email(form.user, self.request)
        return response


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Sets a new password from a reset link and tells the account owner that it happened."""

    def form_valid(self, form):
        response = super().form_valid(form)
        send_password_changed_email(self.user, self.request)
        return response


def activate(request, uidb64, token):
    """Verify the address behind an activation link and mark the account usable."""

    user = account_from_uidb64(uidb64)
    if user is not None and account_activation_token.check_token(user, token):
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        messages.success(request, ACTIVATION_MESSAGE)
        return redirect('signin')

    return render(request, ACTIVATION_FAILED_TEMPLATE, LINK_LIFETIME_CONTEXT)
