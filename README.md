# CTMS — Cargo Transportation Management System

A freight booking and tracking platform. Customers plan multi-leg cargo routes, place orders and follow their status; staff and administrators manage users, orders and enquiries from a control panel.

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

Step 2 is not optional: `djongo` is published only as a source distribution, so setuptools and wheel must already be present to build it. Pinning all three keeps installs reproducible.

Step 5 is required on a fresh clone. Migration files are generated from the models rather than committed, so `makemigrations` must run before the first `migrate`.

---

## Environment variables

Read from `.env` at startup. A missing required variable raises `ImproperlyConfigured` naming the variable; there is no insecure fallback.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | yes | — | Cryptographic signing key |
| `DJANGO_DEBUG` | no | `False` | Enable for development |
| `DJANGO_ALLOWED_HOSTS` | no | `localhost,127.0.0.1` | Comma-separated host names |
| `DJANGO_LOG_LEVEL` | no | `INFO` | Root logger level |
| `MONGODB_URI` | yes | — | MongoDB connection string |
| `MONGODB_NAME` | no | `ctmsdb` | Database name within the cluster |

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
python manage.py findstatic css/styles.css  # show which source file a static path resolves to
python manage.py collectstatic --no-input   # gather static files into staticfiles/
```

`--no-input` suppresses every interactive prompt and takes the default answer, skipping the confirmation to overwrite the output directory.

### Tests

```bash
python manage.py test                       # run the whole suite
python manage.py test apps.accounts         # run one app's tests
```

---

## Project layout

```text
ctms/
├── apps/                             Django applications
│   ├── accounts/                     User accounts and authentication
│   │   ├── migrations/               Empty package; migration files are generated, not committed
│   │   ├── admin.py                  Admin registration and fieldset layout
│   │   ├── apps.py                   Application configuration
│   │   ├── backends.py               Authentication backend that ignores email letter case
│   │   └── models.py                 Account model, its manager, and field length limits
│   └── pages/                        Landing and about pages
│       ├── apps.py                   Application configuration
│       ├── urls.py                   Routes for the two pages
│       └── views.py                  Views rendering their templates
├── config/                           Project configuration
│   ├── db.py                         Database backend adjustment the MongoDB connector needs
│   ├── settings.py                   Every setting, all read from the environment
│   ├── urls.py                       Root URL configuration
│   └── wsgi.py                       WSGI entry point
├── media/                            Uploaded files (MEDIA_ROOT)
│   └── profile-images/default.png    Avatar every account starts with, so it is tracked
├── static/                           Source assets (STATICFILES_DIRS)
│   ├── css/styles.css                Design tokens and the site's own components
│   ├── js/script.js                  Scroll-to-top control and flash message auto-dismiss
│   ├── images/                       Icons, backgrounds, avatars and partner logos
│   ├── videos/                       Landing page hero video
│   └── lib/                          Bootstrap and Font Awesome
├── templates/                        HTML templates
│   ├── includes/                     Navbar, footer and flash messages
│   ├── pages/                        Landing and about pages
│   └── base.html                     Document shell that every page extends
├── .env.example                      Environment variable template, copied to .env
├── .gitattributes                    Line endings, binary handling and vendored paths
├── .gitignore                        Paths kept out of version control
├── LICENSE                           Apache License 2.0
├── manage.py                         Django command-line entry point
├── README.md                         This file
└── requirements.txt                  Pinned dependencies
```

Each package also carries an `__init__.py`.

---

## Notes

**Accounts.** `Account` replaces Django's default user model and authenticates on **email address**, case-insensitively. It is registered as `AUTH_USER_MODEL`, so it must exist before the first `migrate` — Django records the swappable user reference in the migration graph, and changing it later means recreating the database.

**Migrations.** The `migrations/` package is tracked but empty. It cannot be deleted: `django.contrib.admin` and `auth` declare a swappable dependency on the user model, and without that package Django treats `accounts` as unmigrated, skips it during `migrate`, and never creates its table.

**Database.** MongoDB is reached through a SQL-transpiling backend. `config/db.py` declares conditional expressions in `WHERE` clauses unsupported, so Django emits a query form the transpiler can parse. It runs before any connection is opened.

**Front end.** Bootstrap supplies the grid and components. `styles.css` layers the project design on top without redefining a Bootstrap class, with design tokens declared once as custom properties. Layout is mobile-first, headings scale with `clamp()`, and transitions are disabled under `prefers-reduced-motion`.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
