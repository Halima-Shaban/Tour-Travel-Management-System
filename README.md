# GoTrip - Django project

A full-stack Django port of the GoTrip travel UI (originally a static Colorlib
HTML template). The theme's HTML/CSS/JS is untouched in `static/`; everything
dynamic (tours, blog, contact form, accounts) is wired up through real Django
models, views and templates.

## What's included

| App        | Responsible for |
|------------|------------------|
| `core`     | Home, About, Elements pages; the contact form and newsletter signup; site-wide settings (name/email/phone shown in header, footer, contact page) |
| `tours`    | "Favourite Places" cards on the home page and the `/packages/` listing, with search + duration filter |
| `blog`     | Posts, categories, tags, authors, comments, sidebar widgets |
| `accounts` | Sign in / sign up on the theme's dedicated auth page, using Django's built-in User model |

Everything is manageable from `/admin/`.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # adjust if you like; defaults work as-is

python manage.py migrate
python manage.py seed_demo_data   # creates sample tours/posts + an admin user
python manage.py runserver
```

Visit http://127.0.0.1:8000/. The seed command prints an admin username and
password (`admin` / `admin12345`) - **change this before deploying**, or just
run `python manage.py createsuperuser` instead.

## Configuration (`.env`)

All settings have working defaults for local development. See
`.env.example` for the full list. The notable ones:

- `SITE_*` - name, email, phone, address shown across the site.
- `CONTACT_RECIPIENT_EMAIL` / `EMAIL_*` - if unset, contact-form and comment
  notifications aren't emailed anywhere but every submission is still saved
  and visible in `/admin/`. Console backend prints outgoing mail to the
  terminal in development.
- `GOOGLE_MAPS_API_KEY` - optional. Without it, the contact page shows a free
  OpenStreetMap embed instead of the theme's styled Google map.

## Notes on the conversion

- The original template's `contact_process.php` mailed a hard-coded address
  and its contact page had a saved Google Maps snapshot with the template
  author's own API key baked in. Neither was carried over: the contact form
  now saves to the database (and optionally emails whoever you configure),
  and the map key is your own, supplied via `.env`.
- A few assets referenced by the original HTML (`gijgo.min.js`,
  `site.webmanifest`, a couple of background images) weren't present in the
  archive and aren't used by any page, so they were left out.
- Uploaded tour/blog images fall back to the theme's own placeholder images
  when nothing has been uploaded yet, so cards never look broken.
- `frontend_src/scss/` holds the theme's original Sass source, kept for
  reference if you want to customise colours/fonts - it isn't compiled or
  served; `static/css/style.css` is the compiled CSS actually in use.

## Project layout

```
config/            settings, root urls
core/               home/about/elements/contact/newsletter
tours/              tour packages
blog/               posts, comments, sidebar
accounts/           login/signup (theme's auth.html)
templates/          base.html, partials/, and one folder per app
static/             the GoTrip theme (css/js/img/fonts) + auth page assets
media/              uploaded images (created at runtime)
frontend_src/scss/  original Sass source (reference only)
```
