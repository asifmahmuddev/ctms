"""Django settings for the CTMS project.

Secrets and machine-specific values are read from the environment, loaded from a `.env` file. Copy
`.env.example` to `.env` to get started.
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
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


# --- Environment helpers -----------------------------------------------------------------------

def get_env(name, default=None, required=False):
    """Return an environment variable, raising ImproperlyConfigured when a required one is unset."""

    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f'The {name} environment variable is required but is not set. '
            f'Copy .env.example to .env and fill it in.'
        )
    return value


def get_env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


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
    'apps.accounts',
    'apps.pages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES


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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': get_env('DJANGO_LOG_LEVEL', 'INFO')},
}
