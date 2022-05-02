# CTMS — Cargo Transportation Management System

A freight platform. Visitors register, verify their address and sign in; the public landing and about pages sit in front.

| Component | Version |
| --- | --- |
| Python | 3.10.4 |
| Django | 4.0.4 |
| Database | MongoDB |
| Front end | Bootstrap 5.1.3, Font Awesome 5.15.4 |

---

## Setup

Requires Python 3.10.4 and a MongoDB connection string.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate                      # Windows
source .venv/bin/activate                   # Linux / macOS

# 2. Pin the build toolchain
python -m pip install --upgrade "pip==22.0.4" "setuptools==62.1.0" "wheel==0.37.1"

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Create the environment file, then fill in the values
copy .env.example .env                      # Windows
cp .env.example .env                        # Linux / macOS

# 5. Build the database schema and create an administrator
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# 6. Start the server
python manage.py runserver
```

Site: <http://127.0.0.1:8000/> · Admin: <http://127.0.0.1:8000/admin/>

- **Step 2** is not optional: `djongo` ships only as a source distribution, so setuptools and wheel must already be present to build it.
- **Step 4** needs a MongoDB connection string.
- **Step 5** is required on a fresh clone, because migration files are generated from the models rather than committed.

---

## Environment variables

Read from `.env` at startup. A missing required variable raises `ImproperlyConfigured` naming it; there is no insecure fallback.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | yes | — | Cryptographic signing key |
| `DJANGO_DEBUG` | no | `False` | Enable for development |
| `DJANGO_ALLOWED_HOSTS` | no | `localhost,127.0.0.1` | Comma-separated host names |
| `DJANGO_LOG_LEVEL` | no | `INFO` | Level for Django's logs and the project's own |
| `MONGODB_URI` | yes | — | MongoDB connection string |
| `MONGODB_NAME` | no | `ctmsdb` | Database name within the cluster |
| `EMAIL_HOST` | no | `localhost` | Outgoing SMTP server; any provider serves |
| `EMAIL_PORT` | no | `587` | Outgoing mail port |
| `EMAIL_USE_TLS` | no | `True` | Negotiate TLS on connect |
| `EMAIL_HOST_USER` | no | — | Mail account; empty prints messages to the console instead of sending them |
| `EMAIL_HOST_PASSWORD` | no | — | Mail account password, or an app password where the provider requires one |

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Commands

### Development

```bash
python manage.py runserver                  # http://127.0.0.1:8000/
python manage.py runserver 8080             # a different port
python manage.py runserver 0.0.0.0:8000     # reachable from other devices
python manage.py shell                      # interactive shell with Django loaded
python manage.py check                      # system checks
python manage.py test                       # run the test suite
python -m pip check                         # dependency consistency
```

### Database

```bash
python manage.py makemigrations             # detect model changes and write a migration
python manage.py migrate                    # apply migrations
python manage.py showmigrations             # list migrations and which are applied
python manage.py sqlmigrate accounts 0001   # show the statements a migration runs
python manage.py createsuperuser            # prompts for email, username and password
python manage.py changepassword <email>     # reset a password
```

`makemigrations` needs a reachable database, because the backend introspects live collections.

### Static files

```bash
python manage.py findstatic css/styles.css          # show which source file a static path resolves to
python manage.py collectstatic --no-input           # gather static files into staticfiles/
python manage.py collectstatic --clear --no-input   # empty staticfiles/ first, then gather
```

`--no-input` takes the default answer to every prompt. `--clear` empties `staticfiles/` first, which is how a renamed or deleted source file loses its stale copy — `collectstatic` otherwise only adds and overwrites.

---

## Project layout

```text
ctms/
├── apps/                            Django applications
│   ├── accounts/                    User accounts and authentication
│   │   ├── migrations/              Empty package; migration files are generated, not committed
│   │   ├── admin.py                 Admin registration and fieldset layout
│   │   ├── apps.py                  Application configuration
│   │   ├── backends.py              Authentication backend that ignores email letter case
│   │   ├── emails.py                Verification and password notices, sent off the request thread
│   │   ├── forms.py                 Registration, sign-in and password forms
│   │   ├── models.py                Account model, its manager, and field length limits
│   │   ├── tokens.py                One-time token generator behind the activation link
│   │   ├── urls.py                  Routes for registration, sign-in and the password flows
│   │   └── views.py                 Registration, sign-in, sign-out, activation and passwords
│   ├── common/                      Shared helpers, imported by the apps rather than owned by one
│   │   └── forms.py                 Bootstrap control classes and label icons, applied to every form
│   └── pages/                       Landing and about pages
│       ├── apps.py                  Application configuration
│       ├── urls.py                  Routes for the public pages
│       └── views.py                 Landing and about pages
├── config/                          Project configuration
│   ├── db.py                        Database backend adjustment the MongoDB connector needs
│   ├── settings.py                  Every setting, all read from the environment
│   ├── urls.py                      Root URL configuration
│   └── wsgi.py                      WSGI entry point
├── media/                           Uploaded files (MEDIA_ROOT)
│   └── profile-images/default.png   Avatar every account starts with, so it is tracked
├── static/                          Source assets (STATICFILES_DIRS)
│   ├── css/styles.css               Design tokens, and every component the site draws itself with
│   ├── images/                      Icons, backgrounds, avatars and partner logos
│   ├── js/script.js                 Scroll-to-top, flash messages and password reveal
│   ├── lib/                         Bootstrap and Font Awesome
│   └── videos/hero.webm             Landing page hero video
├── templates/                       HTML templates
│   ├── accounts/                    Account and profile pages, and the plain-text emails they send
│   ├── includes/                    Navigation, footer, messages and form fields
│   ├── pages/                       Landing and about pages
│   └── base.html                    Document shell that every page extends
├── .env.example                     Environment variable template, copied to .env
├── .gitattributes                   Line endings, binary handling and vendored paths
├── .gitignore                       Paths kept out of version control
├── LICENSE                          Apache License 2.0
├── manage.py                        Django command-line entry point
├── README.md                        This file
└── requirements.txt                 Pinned dependencies
```

Each package also carries an `__init__.py`.

---

## Notes

**Accounts.** `Account` replaces Django's user model and authenticates on **email address**, case-insensitively. It must exist before the first `migrate`: `AUTH_USER_MODEL` is recorded in the migration graph, and changing it later means recreating the database.

**Authentication.** Registration emails a one-time link that verifies the address; sign-in is refused until it is opened, and a refused attempt sends a fresh link. Sign-out is POST-only, so a prefetched link cannot end a session.

**Link lifetime.** Verification, reset and confirmation links share `ACCOUNT_LINK_LIFETIME_MINUTES` (five), which `PASSWORD_RESET_TIMEOUT` and the pending-address window derive from. A link also dies once used, once the account signs in, or once its password changes — each is folded into the signature.

Two flags decide whether an account works at all rather than what it may do: `is_verified` gates signing in and is set by opening the link registration emails, and `is_active` withdraws the account entirely.

**Passwords.** Django's validators apply, and a replacement identical to the current password is refused. Changing one by either route signs out every other device and emails the owner.

**Email.** Only the account notices are sent, from a background thread so a slow mail server cannot stall a response. With `EMAIL_HOST_USER` unset they print to the terminal.

**Migrations.** The `migrations/` package is tracked but empty, so a fresh clone runs `makemigrations` before its first `migrate`. It cannot be deleted: `django.contrib.admin` and `auth` declare a swappable dependency on `AUTH_USER_MODEL`, and without the package `migrate` fails.

**Database.** MongoDB is reached through a SQL-transpiling backend, and `config/db.py` declares conditional expressions in `WHERE` clauses unsupported — without it ordinary filters fail inside the transpiler.

**Front end.** Bootstrap supplies the grid and components, and `styles.css` layers the project's design on top without redefining a Bootstrap class. Rules are mobile-first, every colour, radius and spacing step is a token at the top of the file, and every text colour clears WCAG AA against the surface it sits on rather than merely against white.

**Form fields.** Every label carries an icon mapped from the field's name in `apps/common/forms.py` and attached by the shared Bootstrap mixin, so a field looks the same wherever it is rendered.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
