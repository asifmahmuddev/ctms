# CTMS — Cargo Transportation Management System

A freight booking and tracking platform. Customers price and place cargo orders across air, sea, road and rail, follow their route and status; staff and administrators manage users, orders and enquiries from a control panel.

| Component | Version |
| --- | --- |
| Python | 3.10.4 |
| Django | 4.0.4 |
| Database | MongoDB |
| Front end | Bootstrap 5.1.3, Font Awesome 5.15.4, Cropper.js 1.5.12, Leaflet 1.8.0 |
| Maps | Leaflet 1.8.0 over OpenStreetMap tiles |
| Geocoding and routing | OpenRouteService |
| Social sign-in | Google OAuth 2.0, through django-allauth 0.50.0 |
| Bot protection | reCAPTCHA v3 |
| Invoices | ReportLab 3.6.9 |
| Serving | Gunicorn 20.1.0, WhiteNoise 6.0.0 |

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
- **Step 4** needs a MongoDB connection string, and for maps a free OpenRouteService key from <https://openrouteservice.org>. Without the key an order is still placed and priced; it simply has no route and no map.
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
| `OPENROUTESERVICE_API_KEY` | no | — | Free routing key; without it an order is placed without a route |
| `GOOGLE_OAUTH_CLIENT_ID` | no | — | OAuth client for Google sign-in; without it the button is not offered |
| `GOOGLE_OAUTH_CLIENT_SECRET` | no | — | Secret for that client, read on the server only |
| `RECAPTCHA_SITE_KEY` | no | — | Rendered into the page so the browser can mint a token |
| `RECAPTCHA_SECRET_KEY` | no | — | Scores a token on the server; empty accepts every submission unweighed |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | — | Origins outside `DJANGO_ALLOWED_HOSTS` that may submit a form, scheme included |
| `DJANGO_HSTS_SECONDS` | no | `3600` | Seconds a browser refuses plain HTTP for the site once HTTPS is live |

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

## Deployment

Host-agnostic: any Linux box, VM or container that runs a WSGI server behind a reverse proxy.

| | Local | Production |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | `False` |
| Server | `manage.py runserver` | Gunicorn behind a reverse proxy |
| Static files | served by `runserver` | collected, then served by WhiteNoise |
| Uploaded files | served by `runserver` | persistent disk, served by the proxy |
| HTTPS | none | terminated by the proxy, which passes `X-Forwarded-Proto` |
| Email | printed to the console | real SMTP credentials |

```bash
python -m pip install -r requirements.txt
python manage.py makemigrations && python manage.py migrate
python manage.py collectstatic --no-input --clear
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

With `DEBUG` off the HTTPS redirect, secure cookies, HSTS and hashed static file names all come on. `DJANGO_SECRET_KEY` must be fresh and `DJANGO_ALLOWED_HOSTS` must name the real hosts, because Django refuses a host it was not given.

- **`SECURE_PROXY_SSL_HEADER` trusts `X-Forwarded-Proto`**, so set it only behind a proxy that really adds it: without the header the redirect loops and every form submission fails its origin check.
- **HSTS is not easily withdrawn.** A browser that has seen it refuses plain HTTP for the full duration whatever the server later says, so start at an hour and raise it once HTTPS is stable.
- **Uploads need a persistent disk.** `config/urls.py` serves `media/` only while `DEBUG` is on, so the proxy must serve `/media/` from a directory a redeploy does not discard.
- Add `https://<host>/accounts/google/login/callback/` to the OAuth client, and the production domain to the reCAPTCHA key pair.
- `python manage.py check --deploy` is silent once this is in place.

---

## Project layout

```text
ctms/
├── apps/                             Django applications
│   ├── accounts/                     User accounts and authentication
│   │   ├── migrations/               Empty package; migration files are generated, not committed
│   │   ├── adapters.py               Which account a Google sign-in belongs to, and how a new one is named
│   │   ├── admin.py                  Admin registration and fieldset layout
│   │   ├── apps.py                   Application configuration
│   │   ├── backends.py               Authentication backend that ignores email letter case
│   │   ├── emails.py                 Verification, confirmation and change notices, sent off the request thread
│   │   ├── forms.py                  Registration, sign-in, password and profile forms
│   │   ├── images.py                 Crops an upload to the square avatar stored on an account
│   │   ├── models.py                 Account model, its manager, and field length limits
│   │   ├── tokens.py                 One-time token generators behind the activation and confirmation links
│   │   ├── urls.py                   Routes for the account flows
│   │   └── views.py                  Registration, sign-in, sign-out, activation, passwords and profile
│   ├── backoffice/                   Control panel for staff and administrators
│   │   ├── apps.py                   Application configuration
│   │   ├── forms.py                  Creating an account, editing one within rank, pricing an order, the company
│   │   ├── urls.py                   Namespaced routes for the panel's pages and actions
│   │   └── views.py                  Dashboard, the tables, the company and account pages, and their actions
│   ├── billing/                      Payments taken against an order, and cards kept for the next
│   │   ├── migrations/               Empty package; migration files are generated, not committed
│   │   ├── admin.py                  Read-only admin listing of payments and kept cards
│   │   ├── apps.py                   Application configuration
│   │   ├── forms.py                  Checkout, which keeps no card number and no security code
│   │   ├── invoices.py               Draws an invoice as a PDF, measured down the page
│   │   ├── models.py                 Payment and SavedCard, and how a receipt is numbered
│   │   ├── responses.py              Hands a drawn invoice to the browser as a download
│   │   ├── signals.py                Opens a payment against every order as it is placed
│   │   ├── urls.py                   Routes for paying, the invoice and the kept cards
│   │   └── views.py                  Settling an order, drawing its invoice, removing a kept card
│   ├── common/                       Shared helpers, imported by the apps rather than owned by one
│   │   ├── context_processors.py     The company, and which ways in a page may offer
│   │   ├── forms.py                  Bootstrap control classes and label icons, applied to every form
│   │   ├── lists.py                  A table that can be searched, narrowed, reordered and paged
│   │   └── recaptcha.py              Scores a submission, and the form mixin that acts on the verdict
│   ├── company/                      The organisation the site represents
│   │   ├── migrations/               Empty package; migration files are generated, not committed
│   │   ├── apps.py                   Application configuration
│   │   └── models.py                 The single record naming the company, its address and how to reach it
│   ├── enquiries/                    Messages sent through the public contact page
│   │   ├── migrations/               Empty package; migration files are generated, not committed
│   │   ├── admin.py                  Read-only admin listing of what visitors sent
│   │   ├── apps.py                   Application configuration
│   │   ├── forms.py                  Contact form and its minimum message length
│   │   ├── models.py                 ContactEnquiry model and field length limits
│   │   ├── urls.py                   Route for the contact page
│   │   └── views.py                  View that records an enquiry and thanks the sender
│   ├── pages/                        Landing, about, services and careers pages
│   │   ├── apps.py                   Application configuration
│   │   ├── content.py                Service and role copy, with the rates read from the transport app
│   │   ├── urls.py                   Routes for the four pages
│   │   └── views.py                  Renders each page with the copy and figures it quotes
│   └── transport/                    Transport orders
│       ├── migrations/               Empty package; migration files are generated, not committed
│       ├── admin.py                  Admin registration and fieldset layout
│       ├── apps.py                   Application configuration
│       ├── forms.py                  Order form, its weight bounds and its route check
│       ├── models.py                 Order model, the modes it ships by, how it is priced and where it stands
│       ├── services.py               Geocoding, road routing and great-circle geometry
│       ├── urls.py                   Routes for placing, listing, reading and cancelling an order
│       └── views.py                  Order placement, the owner's own list and detail, and cancellation
├── config/                           Project configuration
│   ├── db.py                         Database backend adjustment the MongoDB connector needs
│   ├── settings.py                   Every setting, all read from the environment
│   ├── urls.py                       Root URL configuration
│   └── wsgi.py                       WSGI entry point
├── media/                            Uploaded files (MEDIA_ROOT)
│   └── profile-images/default.png    Avatar every account starts with, so it is tracked
├── static/                           Source assets (STATICFILES_DIRS)
│   ├── css/styles.css                Design tokens, and every component the site draws itself with
│   ├── images/                       Icons, backgrounds, avatars and partner logos
│   ├── js/                           Browser behaviour, loaded as written with no build step
│   │   ├── map.js                    Address suggestions and the route map, on the two order pages
│   │   └── script.js                 Scroll-to-top, messages, password reveal, cropping, confirmations, reCAPTCHA, card entry and column widths
│   ├── lib/                          Bootstrap, Font Awesome, Cropper.js and Leaflet
│   └── videos/hero.webm              Landing page hero video
├── templates/                        HTML templates
│   ├── accounts/                     Account and profile pages, and the plain-text emails they send
│   ├── backoffice/                   Control panel dashboard, tables, company page, account page and form
│   ├── billing/                      Checkout, the invoice and the kept cards
│   ├── enquiries/                    Contact page
│   ├── includes/                     Navigation, footer, messages, form fields, detail rows, status pills, the confirm dialogue
│   ├── pages/                        Landing, about, services and careers pages
│   ├── socialaccount/                Provider confirmation, cancellation and failure pages
│   ├── transport/                    Order form, order list and order detail
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

**Accounts.** `Account` replaces Django's user model and authenticates on **email address**, case-insensitively. It must exist before the first `migrate`: `AUTH_USER_MODEL` is recorded in the migration graph, and changing it later means recreating the database.

**Authentication.** Registration emails a one-time link that verifies the address; sign-in is refused until it is opened, and a refused attempt sends a fresh link. Sign-out is POST-only, so a prefetched link cannot end a session.

**Signing in with Google.** The button posts rather than links and the exchange happens on the server, so no other site can start the handshake and the browser never holds the client secret. Google reports only addresses it has checked, so such an account is verified outright and an address already registered is linked to it rather than duplicated.

The link is held by the provider's identifier, not the address, so either side may change its address freely. A provider can be disconnected from the profile editor, but only once a password exists — unlinking the only way in would lock the holder out.

**reCAPTCHA.** Registration, sign-in, password reset and the contact form are scored by reCAPTCHA v3; below `RECAPTCHA_MINIMUM_SCORE` the submission is refused on the form. A token is minted at the moment of submitting because it expires two minutes later, and with no secret key set the check is skipped rather than failing closed.

**Link lifetime.** Verification, reset and confirmation links share `ACCOUNT_LINK_LIFETIME_MINUTES` (five), which `PASSWORD_RESET_TIMEOUT` and the pending-address window derive from. A link also dies once used, once the account signs in, or once its password changes — each is folded into the signature.

**Profile.** Each holder edits their own record only, resolved from the session rather than the URL, and email address, username and password each change on their own page behind the current password. A date of birth must fall between 1900 and one year before today.

**Changing an email address.** The new address is held pending while a one-time link goes to it, and only opening that link moves the account. The address being left is warned both when the change is asked for and when it completes, and changing the password cancels the request outright.

**Profile pictures.** PNG and JPEG only, under 5 MB, with the format read from the file's own bytes rather than its name. Cropped server-side with Pillow to a 512-pixel square; a stored path can outlive its file, so `profile_image_url` falls back to the shared default.

**Public pages.** Landing, about, services and careers, with the copy in `apps/pages/content.py` rather than buried in templates. The services page is built from the transport app's own rate tables, so a quote and a charge cannot describe different things.

**Contact enquiries.** Anyone may send one, signed in or not; staff move each from **New** through **In progress** to **Resolved** or **Closed**. What the visitor wrote is never editable, and only an administrator may delete one.

**Transport orders.** An order names a mode, origin, destination and weight; the cost and the status follow from those and are never read from the submitted form. Pricing is per kilogram plus a distance rate for every thousand kilometres, so a heavy load pays for the distance while a parcel barely notices it, and an order without a route is charged on weight alone.

**Pricing an order by hand.** Staff may set a figure other than the quote, with a reason shown to the account holder beside the price on both the order and the invoice. The reason is what makes it stick: `save()` recomputes the quote every time but only overwrites the price while no reason is recorded, and a settled payment fixes the price until the payment is reversed.

**Paying for an order.** Placing an order opens a payment against it at **Payment Pending**, so no table carries a column that is sometimes blank; paying settles that same record and issues a receipt number. An administrator may mark a settled payment **Refunded** or **Failed**, either of which leaves the amount due again.

**Cards.** The checkout is a demonstration and no money moves. **No card number and no security code is ever stored** — a kept card holds only the brand, last four digits, expiry and name on it, which is how a payment service keeps one on file; paying with a kept card asks for its security code again.

**Entering a card.** An expiry is printed MM/YY, so the slash is written as the digits are typed and appears only once a year digit follows it, which leaves backspace a way out. The field stays a single control, so a browser's own card filler still fills it in one go.

**Invoices.** `/orders/<pk>/invoice/` shows the invoice as a page and `/orders/<pk>/invoice.pdf` hands over the file, drawn by ReportLab on the way out rather than stored, so it always reflects where the payment stands now. Its number derives from the order, so it never changes once issued.

**How an invoice stands.** Page and file both carry a tilted stamp — **PAID** in green, **REFUNDED** amber, **FAILED** red, **PAYMENT PENDING** grey — with the drawn wording shrunk to fit between the stamp's rings. The file names itself, so a reader opens it as its own number rather than as "untitled".

**The course an order runs.** Nine stages — **Pending, Confirmed, Processing, Ready for Pickup, Picked Up, In Transit, Out for Delivery, Delivered, Completed** — and three ways to leave early: **Cancelled**, **Returned**, **Archived**. An order that has left draws no tracker, because leaving is not a point along the way.

**How the tracker is drawn.** The stages fold across the page — three to a row on a desktop, two on a tablet, upright on a phone — with each row running the opposite way to the one above and the line turning at a rounded corner. Each stage draws the line leaving it, so the two halves of a turn meet in the row gap and neither has to know how tall the other's wording made its row.

**Freight is not handed over before it is paid for.** An order cannot reach Ready for Pickup or any stage beyond until its payment is settled; `TransportOrder.may_reach` answers that, and both the dropdown and the route acting on it read it, so withholding the option is presentation and the refusal is the guard. Ending an order early is never blocked.

**Cancelling** is the owner's only while an order is still Pending. From the moment the freight desk confirms it, cancelling is the desk's, at any point.

**Who may do what.** An account is a **member**, **staff**, an **administrator** or a **superuser**: a member books their own orders, staff run the freight desk, an administrator also deletes records and manages accounts, and a superuser appoints administrators. The rule lives on the account as `can_open_backoffice` and `can_administer_backoffice`, so the guards, the navigation and the menus all read one definition.

**Acting on an account.** `Account.manageable_flags_for` answers which flags one account may set on another: a superuser sets `is_admin`, `is_staff`, `is_verified` and `is_active`; an administrator sets the last three, and only on members and staff. Nobody edits their own privileges, and a flag the actor may not set is removed from the form rather than merely hidden — `construct_instance` copies only fields that reach `cleaned_data`.

Two flags decide whether an account works at all rather than what it may do: `is_verified` gates signing in and is set by opening the link registration emails, and `is_active` withdraws the account entirely.

**Control panel.** A back office at `/backoffice/` — dashboard, company, accounts, orders, payments, enquiries — guarded by two mixins: one admits anyone who may open the panel, the other narrows the company and account pages to administrators. Every page and every action carries one, so nothing is guarded by omission, and every action posts. Django's own admin remains at `/admin/` for raw data work.

**Finding a record.** Every table can be searched, narrowed, reordered and paged from the query string, so any view of one is an address that can be shared or bookmarked. `apps/common/lists.py` holds all of this once at **20 rows** a page, and each table declares its own columns, narrowings and orderings.

**Asking before something cannot be undone.** One dialogue serves the whole site and no page reaches for the browser's own confirm box; a destructive control carries what is asked, what it costs and what accepting is called, and the dialogue takes its wording from whichever control raised it. The submission is held until someone accepts, and a keyboard alone can work it — Tab cycles inside it, Escape closes it, and focus returns to the control that opened it.

**Reading a table.** A row lights up under the pointer, and a heading can be dragged wider by the grip at its trailing edge, with the widths kept against the table's own name and a **Reset columns** control to put them back. Only while the rows are real table rows: narrower than a laptop a row is stacked and names its own cells.

Orders and payments are acted on from the record itself rather than through an action column, and accounts open in a tab of their own. Every search, narrowing and ordering is matched against what the page declares before it reaches the database.

**The dashboard** breaks each kind of record down rather than counting it: accounts as one divided bar, orders as bars filling along their course, enquiries as a card per status. Shares are worked out by largest remainder, so the slices come to exactly 100%, and staff see only the breakdowns they act on.

**The account page** shows one account in full and is where its permission flags and every profile detail are settled. The email address, username and password are absent by design: each has its own flow that confirms the change with the account holder.

**Routing.** An address box offers places to pick from, and when both ends are known the journey is worked out as the order is placed and stored with it, so the order page draws its map without asking the service again. Road and rail route over the road network; air and sea, and any land journey the service declines, follow the great circle. Both calls are made from the server, so the key never reaches a browser, and an address typed by hand still places an order — simply without a map.

**Passwords.** Django's validators apply, and a replacement identical to the current password is refused. Changing one by either route signs out every other device and emails the owner.

**Email.** Only the account and order notices are sent, from a background thread so a slow mail server cannot stall a response. With `EMAIL_HOST_USER` unset they print to the terminal.

**The company.** The trading name, full name, contact address, phone and postal address are one record, edited by an administrator from the **Company** tab and read wherever the site names itself — the contact page, the footer, the sign-in pages, both invoices, and the sign-off on every account message. Messages are rendered without a request, so nothing a context processor offers reaches them and the record is passed to those templates explicitly.

**Migrations.** The `migrations/` package is tracked but empty, so a fresh clone runs `makemigrations` before its first `migrate`. It cannot be deleted: `django.contrib.admin` and `auth` declare a swappable dependency on `AUTH_USER_MODEL`, and without the package `migrate` fails.

**Database.** MongoDB is reached through a SQL-transpiling backend, and `config/db.py` declares conditional expressions in `WHERE` clauses unsupported — without it ordinary filters fail inside the transpiler. `DecimalField` is avoided throughout: the connector writes `Decimal128` and registers no converter to read one back.

**Front end.** Bootstrap supplies the grid and components, Leaflet draws the maps over OpenStreetMap tiles, and `styles.css` layers the project's design on top without redefining a Bootstrap class. Rules are mobile-first, every colour, radius and spacing step is a token at the top of the file, and every text colour clears WCAG AA against the surface it sits on rather than merely against white.

**Form fields.** Every label carries an icon mapped from the field's name in `apps/common/forms.py` and attached by the shared Bootstrap mixin, so a field looks the same wherever it is rendered. The profile groups — personal details, contact, social links — come from one definition that both the holder's own editor and the administrator's account page lay themselves out from.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
