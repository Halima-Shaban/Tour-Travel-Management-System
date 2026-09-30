# Architecture

Django 5.1 monolith, server-rendered templates, SQLite by default (any Django database works).

```
config/      settings (env driven), root URLs
core/        SiteSettings (customization), contact messages, newsletter, home/about/contact,
             shared helpers: StyledFormMixin, template tags (ui), seed_demo_data command
accounts/    Profile (role, guide fields), login/signup/role redirect, my bookings, permissions
tours/       Destination, Tour, Booking, Review - public listing/detail/booking flow
blog/        Category, Post, Comment
dashboard/   Admin dashboard views (no models) + analytics helpers
guide/       Guide dashboard views (no models)
chatbot/     Conversation, Message, knowledge builder, Groq/offline engine, JSON endpoints
templates/   base.html (public), dash_base.html (shared dashboard shell), per-app folders, partials/
static/      css/theme.css (tokens), site.css, dashboard.css, chatbot.css; js/*; vendor/ (libraries)
tests/       end-to-end test suite
docs/        this documentation
```

## Key design decisions
- **Roles** via a `Profile.role` field rather than Django groups: simple to reason about and query.
  `accounts/permissions.py` provides `AdminRequiredMixin`, `GuideRequiredMixin` and the
  `admin_required` / `guide_required` decorators (login redirect for guests, 403 for wrong role).
- **Guide data isolation** is enforced in the query (`Booking.objects.filter(tour__guide=user)`),
  not in templates.
- **Booking integrity**: price is snapshotted (`unit_price`) at booking time; `total_price` is always
  recomputed on save; capacity per departure date is validated against non-cancelled bookings;
  tours/destinations with bookings are `PROTECT`ed from deletion.
- **Analytics** (`dashboard/analytics.py`) are pure queryset functions reused by both dashboards.
- **Customization** is a cached singleton exposed to every template as `site` by
  `core.context_processors.site`.
- **Front end**: Bootstrap 5 + a small token-based design layer; no build step. Third-party
  libraries are vendored in `static/vendor/` (see its README for versions).

## Data model

```
User 1─1 Profile(role)
User 1─* Tour (as guide)         Destination 1─* Tour 1─* Booking *─1 User (optional, guests allowed)
Tour 1─* Review *─1 User (one per user per tour)
Conversation 1─* Message         Post *─1 Category, Post 1─* Comment
```
