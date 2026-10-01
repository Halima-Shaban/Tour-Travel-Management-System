# GoTrip - Tour & Travel Management System

A complete Django platform for tour operators: a modern public booking website, an **admin
dashboard**, a **tour-guide dashboard**, live **no-code customization** and an **AI travel
assistant** powered by Groq.

## Features

| Area | Highlights |
|------|------------|
| **Public site** | Hero search, destinations, tour listing with filters/sorting, tour pages (itinerary, guide, reviews, live price), booking with capacity & guide-availability checks, **Stripe payment**, customer booking page (progress tracker, traveler names, **chat with the guide**), blog, contact, newsletter, dark mode, responsive |
| **Admin dashboard** `/dashboard/` | KPIs & charts, bookings workflow + CSV export, **needs-guide queue & reassignment**, payments & **Stripe refunds**, trip conversations, tours/destinations/blog CRUD, guide performance, users & roles, reviews, inbox, subscribers, chatbot logs |
| **Guide dashboard** `/guide/` | **Accept / decline trip requests**, schedule calendar with **time off**, trip details with **participant lists**, printable manifests, **chat with travelers**, overlap warnings, reviews, profile |
| **Integration** | One booking workflow service shared by all three, plus in-app **notifications** (bell on every page) and email for key events |
| **Customization** `/dashboard/settings/` | Name, logo, colours, font, corner radius, home-page content & sections, contact/social links, currency, booking on/off, cancellation policy, chatbot persona - live preview, no code |
| **Chatbot** | Groq LLM (Llama 3.3 70B + automatic fallback model) grounded on your real tours and policies, replies in the visitor's language, tour cards, rate limiting, offline database-backed mode when no key/network |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add GROQ_API_KEY (chatbot) and STRIPE_* keys (payments)
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

| Role | Login | Lands on |
|------|-------|----------|
| Admin | `admin` / `admin12345` | `/dashboard/` |
| Guide | `guide` / `guide12345` | `/guide/` |
| Customer | `customer` / `customer12345` | `/account/bookings/` |

Change these before deploying. Tests: `python manage.py test tests`.

## Documentation

Full docs live in [`docs/`](docs/README.md): [installation](docs/installation.md) ·
[configuration](docs/configuration.md) · [customization](docs/customization.md) ·
[admin dashboard](docs/admin-dashboard.md) · [guide dashboard](docs/guide-dashboard.md) ·
[booking workflow](docs/workflow.md) · [payments](docs/payments.md) · [chatbot](docs/chatbot.md) · [architecture](docs/architecture.md) · [deployment](docs/deployment.md)

## Project layout

```
config/      settings (env driven) & URLs
core/        site settings/customization, home/about/contact, newsletter, shared helpers
accounts/    roles (Profile), auth, customer bookings, permission helpers
tours/       destinations, tours, bookings, reviews
blog/        posts, categories, comments
dashboard/   admin dashboard + analytics
guide/       guide dashboard
chatbot/     AI assistant (Groq + offline engine)
notifications/ in-app notifications (bell)
messaging/   traveler ↔ guide ↔ office chat per booking
payments/    Stripe Checkout, webhook, refunds
templates/   page templates and partials
static/      design tokens, site/dashboard/chatbot CSS, JS
tests/       test suite
docs/        documentation
```

Tech: Django 5.1 · Bootstrap 5.3 · Chart.js 4 · FullCalendar 6 · Groq API · Stripe. No front-end build step;
libraries are bundled in `static/vendor/`, so no CDN is needed.
