"""Django settings for the CTMS project.

Secrets and machine-specific values come from the environment; copy `.env.example` to `.env`.
"""

import os
from pathlib import Path

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from config.db import configure_database_backend

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# --- Constants ---------------------------------------------------------------------------------

TRUTHY_VALUES = {'1', 'true', 'yes', 'on'}

DEFAULT_ALLOWED_HOSTS = ['localhost', '127.0.0.1']
DEFAULT_DATABASE_NAME = 'ctmsdb'

SESSION_LIFETIME_SECONDS = 60 * 60 * 24
ACCOUNT_LINK_LIFETIME_MINUTES = 5
MAX_FORM_DATA_BYTES = 5 * 1024 * 1024

SMTP_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
CONSOLE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_EMAIL_HOST = 'localhost'
DEFAULT_EMAIL_PORT = '587'
DEFAULT_SENDER_ADDRESS = 'no-reply@ctms-asifmahmuddev.com'

DEFAULT_LOG_LEVEL = 'INFO'

# The routing service answers slowly for a long route, and a request thread must not wait for ever.
ROUTING_REQUEST_TIMEOUT_SECONDS = 20

# reCAPTCHA answers with a score, not a verdict, so name the refusal line and how long to wait.
RECAPTCHA_MINIMUM_SCORE = 0.5
RECAPTCHA_REQUEST_TIMEOUT_SECONDS = 10


# --- Environment helpers -----------------------------------------------------------------------

def get_env(name, default=None, required=False):
    """Return an environment variable, treating a blank value as unset so a cleared key falls back."""

    value = os.environ.get(name) or default
    if required and not value:
        raise ImproperlyConfigured(
            f'The {name} environment variable is required but is not set. '
            f'Copy .env.example to .env and fill it in.'
        )

    return value


def get_env_bool(name, default=False):
    """Return an environment variable as a flag, treating a blank value as unset so it falls back."""

    value = os.environ.get(name, '').strip().lower()
    return value in TRUTHY_VALUES if value else default


def get_env_list(name, default=()):
    """Return a comma-separated environment variable parsed as a list of trimmed strings."""

    value = os.environ.get(name)
    if not value:
        return list(default)

    return [item.strip() for item in value.split(',') if item.strip()]


# --- Core --------------------------------------------------------------------------------------

DEBUG = get_env_bool('DJANGO_DEBUG', False)

SECRET_KEY = get_env('DJANGO_SECRET_KEY', required=True)

ALLOWED_HOSTS = get_env_list('DJANGO_ALLOWED_HOSTS', DEFAULT_ALLOWED_HOSTS)

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # The sites framework stays out: credentials are read from settings, not from a SocialApp row.
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'apps.accounts',
    'apps.backoffice',
    'apps.billing',
    'apps.company',
    'apps.enquiries',
    'apps.pages',
    'apps.transport',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.common.context_processors.sign_in_options',
                'apps.common.context_processors.company_details',
            ],
        },
    },
]


# --- Database ----------------------------------------------------------------------------------
# ENFORCE_SCHEMA is off so that documents written before a model gains a field remain readable.

configure_database_backend()

DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': get_env('MONGODB_NAME', DEFAULT_DATABASE_NAME),
        'ENFORCE_SCHEMA': False,
        'CLIENT': {
            'host': get_env('MONGODB_URI', required=True),
        },
    }
}


# --- Authentication ----------------------------------------------------------------------------

AUTH_USER_MODEL = 'accounts.Account'

AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.CaseInsensitiveModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'signin'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

SESSION_COOKIE_AGE = SESSION_LIFETIME_SECONDS

# Verification, reset and address links share this timeout, and the emails quote the same constant.
PASSWORD_RESET_TIMEOUT = ACCOUNT_LINK_LIFETIME_MINUTES * 60


# --- Social sign-in ----------------------------------------------------------------------------
# Credentials come from the environment, not a database row, and only the provider flow is used.

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': get_env('GOOGLE_OAUTH_CLIENT_ID', ''),
            'secret': get_env('GOOGLE_OAUTH_CLIENT_SECRET', ''),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
    },
}

SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.GoogleAccountAdapter'

# Google has already verified the address, so a second link would ask a question already answered.
ACCOUNT_EMAIL_VERIFICATION = 'none'


# --- reCAPTCHA ---------------------------------------------------------------------------------
# The site key is rendered into the page to mint a token; the secret key never leaves this process.

RECAPTCHA_SITE_KEY = get_env('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET_KEY = get_env('RECAPTCHA_SECRET_KEY', '')


# --- Routing -----------------------------------------------------------------------------------
# Geocoding and routing are proxied through this project, so the key never reaches a browser.

OPENROUTESERVICE_API_KEY = get_env('OPENROUTESERVICE_API_KEY')


# --- Email -------------------------------------------------------------------------------------
# Plain SMTP, so any provider serves; with no credentials the console backend prints each message.

EMAIL_HOST = get_env('EMAIL_HOST', DEFAULT_EMAIL_HOST)
EMAIL_PORT = int(get_env('EMAIL_PORT', DEFAULT_EMAIL_PORT))
EMAIL_USE_TLS = get_env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = get_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_env('EMAIL_HOST_PASSWORD', '')

EMAIL_BACKEND = SMTP_EMAIL_BACKEND if EMAIL_HOST_USER else CONSOLE_EMAIL_BACKEND
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or DEFAULT_SENDER_ADDRESS


# --- Internationalization ----------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- Static and media --------------------------------------------------------------------------
# STATIC_ROOT is a collectstatic destination and must never also appear in STATICFILES_DIRS.

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Weighs a body without its uploads, so it bounds form fields; a picture is checked as it validates.
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_FORM_DATA_BYTES


# --- Messages ----------------------------------------------------------------------------------
# Tags double as Bootstrap alert classes and are rendered directly into the alert markup.

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}


# --- Logging -----------------------------------------------------------------------------------
# Naming the `django` logger replaces Django's own handlers so nothing prints twice, and clears its children, so the access log is declared again.

LOG_LEVEL = get_env('DJANGO_LOG_LEVEL', DEFAULT_LOG_LEVEL)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'},
        'access': {'()': 'django.utils.log.ServerFormatter', 'format': '[{server_time}] {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'access': {'class': 'logging.StreamHandler', 'formatter': 'access'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'django.server': {'handlers': ['access'], 'level': LOG_LEVEL, 'propagate': False},
    },
    'root': {'handlers': ['console'], 'level': LOG_LEVEL},
}


# --- Production --------------------------------------------------------------------------------
# Applied with DEBUG off only, so development is never forced onto HTTPS nor needs a manifest.

CSRF_TRUSTED_ORIGINS = get_env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
HSTS_SECONDS = int(get_env('DJANGO_HSTS_SECONDS', '3600'))

if not DEBUG:
    # Tells Django the proxy terminated TLS; without it the redirect loops and every form fails.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = HSTS_SECONDS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Serves each file under a content-derived name, resolved through collectstatic's manifest.
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
