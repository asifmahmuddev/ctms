"""Views for registration, authentication, activation, password management and the profile."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView

from apps.company.models import CompanyProfile

from .emails import send_activation_email, send_email_change_requested_email, send_email_changed_email, send_password_changed_email, send_pending_email_confirmation
from .forms import EmailChangeForm, ProfileForm, ProfileImageForm, RegistrationForm, SignInForm, UsernameChangeForm
from .images import store_profile_image
from .models import PENDING_EMAIL_FIELDS
from .tokens import account_activation_token, email_change_token

Account = get_user_model()

SIGN_UP_TEMPLATE = 'accounts/signup.html'
SIGN_IN_TEMPLATE = 'accounts/signin.html'
ACTIVATION_FAILED_TEMPLATE = 'accounts/activation-failed.html'
PROFILE_TEMPLATE = 'accounts/profile.html'
PROFILE_EDIT_TEMPLATE = 'accounts/profile-edit.html'
EMAIL_CHANGE_TEMPLATE = 'accounts/email-change.html'
EMAIL_CHANGE_FAILED_TEMPLATE = 'accounts/email-change-failed.html'
USERNAME_CHANGE_TEMPLATE = 'accounts/username-change.html'

LINK_LIFETIME_MINUTES = settings.ACCOUNT_LINK_LIFETIME_MINUTES

# Every page and message that states how long a link lasts renders it from here.
LINK_LIFETIME_CONTEXT = {'link_lifetime_minutes': LINK_LIFETIME_MINUTES}

SIGN_UP_MESSAGE = (
    f'Account created. Open the verification link we emailed you. '
    f'It will expire in {LINK_LIFETIME_MINUTES} minute{pluralize(LINK_LIFETIME_MINUTES)}.'
)
SIGN_IN_MESSAGE = 'You are now signed in as {email}.'
SIGN_OUT_MESSAGE = 'You have been signed out of your CTMS account.'
ACTIVATION_MESSAGE = 'Email address verified. You can sign in now.'
PROFILE_SAVED_MESSAGE = 'Your profile has been updated.'
PROFILE_IMAGE_SAVED_MESSAGE = 'Your profile picture has been updated.'
EMAIL_CHANGE_SENT_MESSAGE = (
    'Confirm the change by opening the link we emailed to {email}. '
    f'It will expire in {LINK_LIFETIME_MINUTES} minute{pluralize(LINK_LIFETIME_MINUTES)}.'
)
EMAIL_CHANGED_MESSAGE = 'Your email address is now {email}.'
USERNAME_CHANGED_MESSAGE = 'Your username is now {username}.'

# Selects which sentence the confirmation failure page renders as its subtitle.
EXPIRED_LINK_REASON = 'expired'
TAKEN_ADDRESS_REASON = 'taken'


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

        # Signing in lands on the index page, so the sweep account pages do is repeated here.
        user.forget_lapsed_email_change()

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
    """Emails a reset link, signed off by the company the way every other account message is.

    Rendered without a request, so no context processor runs and the company is passed in here, read
    per request because the record is corrected while the site is running.
    """

    @property
    def extra_email_context(self):
        return {**LINK_LIFETIME_CONTEXT, 'company': CompanyProfile.current()}


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


class AccountPageMixin(LoginRequiredMixin):
    """Requires a signed-in account, and forgets an address change whose link lapsed unconfirmed.

    Every page reading the account passes through here, and the sweep writes once, clearing what it tests.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            request.user.forget_lapsed_email_change()

        return super().dispatch(request, *args, **kwargs)


class ProfileView(AccountPageMixin, TemplateView):
    """Shows the signed-in account's own details. The template reads them from `user`."""

    template_name = PROFILE_TEMPLATE


class ProfileEditView(AccountPageMixin, UpdateView):
    """Edits the details that need no confirmation, and hosts the picture uploader beside them."""

    form_class = ProfileForm
    template_name = PROFILE_EDIT_TEMPLATE
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        """Edit the signed-in account, which is the only record this page may touch."""

        return self.request.user

    def get_context_data(self, **kwargs):
        return super().get_context_data(image_form=ProfileImageForm(), **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, PROFILE_SAVED_MESSAGE)
        return response


class CredentialChangeView(AccountPageMixin, FormView):
    """Base for the pages that change how an account is identified, once its password is confirmed.

    Each form checks that password against the signed-in account, which is handed to it from here.
    """

    success_url = reverse_lazy('profile')

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'user': self.request.user}


class EmailChangeView(CredentialChangeView):
    """Records the address an account asks to move to and emails that address the confirming link."""

    form_class = EmailChangeForm
    template_name = EMAIL_CHANGE_TEMPLATE

    def form_valid(self, form):
        user = self.request.user
        user.pending_email = form.cleaned_data['email']
        user.pending_email_requested_at = timezone.now()
        user.save(update_fields=PENDING_EMAIL_FIELDS)

        send_pending_email_confirmation(user, self.request)

        # A change nobody asked for is noticed at the old address, so it hears of the request too.
        send_email_change_requested_email(user, self.request)

        messages.success(self.request, EMAIL_CHANGE_SENT_MESSAGE.format(email=user.pending_email))
        return super().form_valid(form)


class UsernameChangeView(CredentialChangeView):
    """Renames the account."""

    form_class = UsernameChangeForm
    template_name = USERNAME_CHANGE_TEMPLATE

    def form_valid(self, form):
        user = self.request.user
        user.username = form.cleaned_data['username']
        user.save(update_fields=['username'])

        messages.success(self.request, USERNAME_CHANGED_MESSAGE.format(username=user.username))
        return super().form_valid(form)


def confirm_email_change(request, uidb64, token):
    """Move an account to the address it asked for, once the link sent to that address is opened.

    Answered without a session, since the address is usually read in a browser never signed in from.
    """

    user = account_from_uidb64(uidb64)
    if user is None or not user.email_change_is_pending or not email_change_token.check_token(user, token):
        return render(request, EMAIL_CHANGE_FAILED_TEMPLATE, {'reason': EXPIRED_LINK_REASON, **LINK_LIFETIME_CONTEXT})
    if Account.objects.email_is_taken(user.pending_email, user.pk):
        return render(request, EMAIL_CHANGE_FAILED_TEMPLATE, {'reason': TAKEN_ADDRESS_REASON, **LINK_LIFETIME_CONTEXT})

    previous_email = user.email
    user.email = user.pending_email
    user.pending_email = None
    user.pending_email_requested_at = None
    user.save(update_fields=('email', *PENDING_EMAIL_FIELDS))

    send_email_changed_email(user, previous_email, request)
    messages.success(request, EMAIL_CHANGED_MESSAGE.format(email=user.email))
    return redirect('profile')


@login_required
@require_POST
def change_profile_image(request):
    """Crop an uploaded picture to the selected square and store it as the account's avatar."""

    form = ProfileImageForm(request.POST, request.FILES)
    if form.is_valid():
        store_profile_image(request.user, form.cleaned_data['image'], form.selection())
        messages.success(request, PROFILE_IMAGE_SAVED_MESSAGE)
    else:
        # The cropper fills the selection, so an unusable one must be reported, not just the picture.
        for field_errors in form.errors.values():
            messages.error(request, field_errors[0])

    return redirect('profile_edit')
