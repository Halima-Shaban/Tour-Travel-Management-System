# GoTrip — Complete System Documentation

**GoTrip** is a production-ready, full-stack Tour & Travel Management System built with **Django 5.1**. It powers public booking discovery, traveler management, dedicated tour guide workspaces, an administrative control panel, no-code branding customization, an AI travel assistant, and transactional email verification via SMTP.

---

## Table of Contents

1. [Executive Overview & Tech Stack](#1-executive-overview--tech-stack)
2. [Architecture & Directory Structure](#2-architecture--directory-structure)
3. [Data Models & Database Schema](#3-data-models--database-schema)
4. [User Roles, Authentication & Email OTP](#4-user-roles-authentication--email-otp)
5. [Core Application Modules & Workflows](#5-core-application-modules--workflows)
   - [5.1 Tours & Booking Workflow Engine](#51-tours--booking-workflow-engine)
   - [5.2 Tour Guide Operations Portal](#52-tour-guide-operations-portal)
   - [5.3 Admin Operations & Analytics](#53-admin-operations--analytics)
   - [5.4 Messaging & In-App Notifications](#54-messaging--in-app-notifications)
   - [5.5 AI Travel Assistant (Chatbot)](#55-ai-travel-assistant-chatbot)
   - [5.6 Payments & Stripe Gateway](#56-payments--stripe-gateway)
   - [5.7 No-Code Live Theme Customizer](#57-no-code-live-theme-customizer)
   - [5.8 Email Delivery System](#58-email-delivery-system)
6. [Complete Route & Endpoint Reference](#6-complete-route--endpoint-reference)
7. [Configuration Reference (`.env`)](#7-configuration-reference-env)
8. [Installation, Local Development & Testing](#8-installation-local-development--testing)
9. [Production Deployment Checklist & Security](#9-production-deployment-checklist--security)

---

## 1. Executive Overview & Tech Stack

GoTrip provides a unified multi-portal architecture serving three distinct personas:
1. **Public Travelers / Customers**: Discover tours, check real-time departure availability, pay securely, manage traveler rosters, chat directly with guides, and track itinerary updates.
2. **Tour Guides**: Review trip assignments, accept or decline departure requests, log unavailability/vacation days, view participant manifests with dietary/emergency notes, and communicate with travelers.
3. **Office Administrators**: Oversee company KPIs, manage tour inventory and destinations, reassign guides, issue Stripe refunds, moderate reviews, handle customer contact inquiries, and configure live site branding without writing code.

### Technology Stack

| Layer | Component | Description |
|---|---|---|
| **Backend Framework** | Django 5.1 (Python 3.10 – 3.14) | Robust monolith with class-based and functional views |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Relational database with foreign key integrity and ACID guarantees |
| **Frontend & UI** | Bootstrap 5.3 + Vanilla CSS tokens | Responsive design with light/dark theme support |
| **Interactive Components** | FullCalendar 6, Chart.js 4 | Vendored locally in `static/vendor/` (zero CDN dependencies) |
| **AI Assistant** | Groq API (`llama-3.3-70b-versatile`) | Real-time OpenAI-compatible API with fallback to offline DB search |
| **Payments** | Stripe Checkout & Webhooks | Hosted Checkout sessions, cryptographic webhook verification, refunds |
| **Mail Transport** | Gmail SMTP / Any standard SMTP | TLS-encrypted email delivery with local debug copy capture |

---

## 2. Architecture & Directory Structure

```
halima/
├── config/              # Project settings, URLs, WSGI, Python 3.14 compatibility layer
├── core/                # SiteSettings (branding/customizer), home/about/contact views, context processors
├── accounts/            # User authentication, Profile model, Email OTP verification, permissions
├── tours/               # Destinations, Tours, Bookings, Participants, GuideUnavailability, Reviews
├── guide/               # Guide dashboard, manifest, calendar, accept/decline flows
├── dashboard/           # Admin dashboard, analytics calculations, catalog CRUD, settings views
├── messaging/           # Booking-scoped chat threads and messages (traveler ↔ guide ↔ admin)
├── notifications/       # In-app notification bell, mark-read API, activity alerts
├── chatbot/             # AI assistant, Groq integration, offline keyword matcher, chat history
├── payments/            # Stripe integration, payment intent handling, refunds, webhook receivers
├── blog/                # Travel articles, categories, comments
├── static/              # CSS design tokens, JavaScript modules, vendored libraries
├── templates/           # Server-rendered HTML templates organized by application
├── sent_emails/         # Local debug inspection folder storing rendered OTPs and emails
├── tests/               # 109 automated unit, integration, and security tests
├── docs/                # Modular and master markdown documentation
├── .env                 # Environment configuration (ignored in version control)
└── manage.py            # Django CLI entrypoint
```

---

## 3. Data Models & Database Schema

### Entity-Relationship Diagram

```
User (django.contrib.auth)
  │── 1:1 ── Profile (role, phone, bio, avatar, languages)
  │── 1:N ── EmailOTP (code, purpose, expires_at, is_used)
  │── 1:N ── Notification (recipient, actor, verb, target, is_read)
  │── 1:N ── GuideUnavailability (guide, start_date, end_date, reason)
  │── 1:N ── Review (tour, user, rating, comment, is_approved)
  │
Destination
  │── 1:N ── Tour (title, slug, price, duration_days, max_group_size, guide)
               │── 1:N ── Booking (reference, user, travel_date, travelers, status, payment_status, guide)
                            │── 1:N ── Participant (full_name, age, dietary, emergency_contact)
                            └── 1:1 ── MessageThread
                                         └── 1:N ── ChatMessage (sender, message, created_at)
```

### Key Models Summary

- **`core.SiteSettings`**: Singleton model storing brand identity (name, tagline, logo), color palette (`primary_color`, `secondary_color`), font family, radius, currency symbol, hero headlines, features, testimonials, contact details, and chatbot persona instructions.
- **`accounts.Profile`**: Extends Django's `User` with `role` (`customer`, `guide`, `admin`), phone number, biography, languages spoken, and avatar.
- **`accounts.EmailOTP`**: Stores 6-digit cryptographic verification codes, purpose (`signup` or `reset_password`), expiration timestamp (10 minutes), attempt counter, and verification status.
- **`tours.Tour`**: Travel package with destination, duration, difficulty, pricing, itinerary schedule, inclusions, exclusions, and default assigned guide.
- **`tours.Booking`**: Central booking entity with unique human-readable reference (e.g. `BK-ABC12345`), departure date, head count, unit/total price, booking status, payment status, and guide response status.
- **`tours.Participant`**: Individual roster traveler under a booking with name, age category, dietary restrictions, and emergency contact details.
- **`tours.GuideUnavailability`**: Calendar blockout dates logged by guides for vacation or illness.
- **`messaging.MessageThread` & `ChatMessage`**: Dedicated three-way chat thread created automatically for every booking between the traveler, the assigned tour guide, and the office team.

---

## 4. User Roles, Authentication & Email OTP

### Role Hierarchy & Permissions

1. **Administrator (`role='admin'` or `is_superuser=True`)**:
   - Access to `/dashboard/` and `/django-admin/`.
   - Full read/write access to all bookings, tours, users, payments, and site settings.
2. **Tour Guide (`role='guide'`)**:
   - Access to `/guide/`.
   - Strictly isolated to bookings where `booking.guide == request.user`.
   - Cannot view other guides' schedules, financial turnover, or administrative settings.
3. **Customer (`role='customer'`)**:
   - Access to public site, tour booking flows, `/account/bookings/`, profile, and booking chat.

### Email OTP Verification System

To prevent spam registrations and enable self-service password recovery, GoTrip uses a 6-digit One-Time Password (OTP) verification pipeline:

```
[User Submits Form]
         │
         ▼
[EmailOTP.generate_otp()] ──► 6-Digit Cryptographic Code (10-min TTL)
         │
         ▼
[send_otp_email()] ───────┬──► Sends Branded HTML via Gmail SMTP (TLS)
                          └──► Writes backup to sent_emails/latest_otp.txt
         │
         ▼
[User Submits OTP] ───────► Validates single-use code & max 5 attempts
         │
   ┌─────┴──────────────┐
   ▼                    ▼
[Signup Flow]       [Reset Password Flow]
user.is_active=True  user.set_password()
auto-login user      redirect to login
```

- **Rate Limiting**: Users must wait **45 seconds** before requesting another OTP resend to prevent email flooding.
- **Security**: Codes expire after **10 minutes** and are invalidated after 5 incorrect attempts.

---

## 5. Core Application Modules & Workflows

### 5.1 Tours & Booking Workflow Engine

All booking state transitions are centralized in [`tours/services.py`](file:///c:/Users/user/Desktop/project/halima/tours/services.py) to guarantee business rules, notifications, and data integrity:

```
                  ┌───────────────┐
                  │ Customer Book │
                  └───────┬───────┘
                          ▼
                  [Status: PENDING]
                  [Guide: PENDING]
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
      [Guide Accepts]           [Guide Declines]
      Guide Status: ACCEPTED    Guide Status: DECLINED
      Status: CONFIRMED         Status: PENDING (Needs guide queue)
             │                         │
             ▼                         ▼
      [Stripe Payment]          [Admin Reassigns Guide]
      Payment: PAID             New Guide: PENDING
```

- **Capacity Protection**: Checks remaining seats per departure date before confirming.
- **Financial Snapshot**: Snapshots unit price at checkout time so future price changes do not alter existing contracts.

### 5.2 Tour Guide Operations Portal (`/guide/`)

- **Departure Requests**: Instant accept or decline buttons for assigned trips.
- **Interactive Calendar**: FullCalendar integration displaying confirmed departures and blockout days.
- **Trip Manifests**: Printable participant rosters with emergency contact numbers and dietary requirements.
- **Schedule Conflict Alerting**: Automatic warning if a newly requested tour overlaps with an existing assignment or approved leave.

### 5.3 Admin Operations & Analytics (`/dashboard/`)

- **Executive KPI Cards**: Real-time gross volume, net revenue, active bookings, completed tours, and guide count.
- **Needs-Guide Queue**: Flags departures where the guide declined or is unassigned.
- **Catalog Management**: Create, edit, and toggle active visibility for tours and destinations.
- **Data Export**: One-click CSV export of booking records for accounting.
- **Review Moderation**: Approve or hide customer reviews before they appear publicly.

### 5.4 Messaging & In-App Notifications

- **Booking Chat**: Every booking automatically receives an isolated thread (`/account/messages/` or `/guide/messages/`). Traveler, guide, and admin can exchange updates without sharing personal phone numbers.
- **Notification Bell**: Navbar dropdown powered by `notifications/` alerting users when a trip is booked, confirmed, reassigned, or cancelled.

### 5.5 AI Travel Assistant (Chatbot)

- **Engine**: Powered by Groq API (`llama-3.3-70b-versatile` with automatic fallback to `llama-3.1-8b-instant`).
- **Grounding**: Automatically queries active database tours, destinations, pricing, and cancellation policies to build the LLM system prompt.
- **Offline Mode**: If the Groq API key is omitted or network connectivity is unavailable, the chatbot seamlessly switches to an internal keyword search engine answering questions directly from the database.
- **Abuse Prevention**: Enforces a configurable per-session rate limit (`CHATBOT_MAX_MESSAGES_PER_HOUR=40`).

### 5.6 Payments & Stripe Gateway

- **Stripe Checkout**: Generates hosted checkout sessions with order line items and metadata matching the booking reference.
- **Webhooks (`/payments/webhook/`)**: Listens for `checkout.session.completed` events using Stripe signature verification to mark bookings as `PAID`.
- **Admin Refunds**: Administrators can issue partial or full Stripe refunds directly from the booking detail screen in the admin dashboard.

### 5.7 No-Code Live Theme Customizer (`/dashboard/settings/`)

Administrators can customize the customer-facing website without altering template files:
- **Branding**: Agency name, logo upload, footer description.
- **Styling**: Primary color, secondary accent color, typography font family, button corner radius.
- **Content Blocks**: Hero banner titles, subtitles, call-to-action buttons, value propositions, and customer reviews.
- **Operational Policies**: Currency symbol (`$`, `€`, `£`, `EGP`), online booking toggle, cancellation policy rules, and custom chatbot personality prompt.

### 5.8 Email Delivery System

- **Transport**: Standard SMTP via `django.core.mail.backends.smtp.EmailBackend`.
- **Default Provider**: Gmail SMTP (`smtp.gmail.com:587` with TLS).
- **Template Rendering**: Sends dual-format messages (HTML styled card + plain text fallback).
- **Local Inspection**: Writes copies to [`sent_emails/latest_otp.txt`](file:///c:/Users/user/Desktop/project/halima/sent_emails/latest_otp.txt) and [`sent_emails/latest_email.html`](file:///c:/Users/user/Desktop/project/halima/sent_emails/latest_email.html) for effortless local testing.

---

## 6. Complete Route & Endpoint Reference

### Public Routes
| URL | View | Description |
|---|---|---|
| `/` | `core:home` | Homepage with hero search, featured tours, destinations |
| `/about/` | `core:about` | Company background and values |
| `/contact/` | `core:contact` | Contact form with database logging |
| `/newsletter/` | `core:newsletter` | Newsletter email subscription |
| `/tours/` | `tours:list` | Tour directory with filtering and sorting |
| `/tours/destinations/` | `tours:destinations` | All destinations grid |
| `/tours/destinations/<slug>/` | `tours:destination_detail` | Destination tours |
| `/tours/<slug>/` | `tours:detail` | Tour page with itinerary, reviews, booking widget |
| `/tours/<slug>/book/` | `tours:book` | Departure date selection and booking form |
| `/tours/booking/<ref>/` | `tours:booking_detail` | Booking confirmation and traveler hub |
| `/blog/` | `blog:list` | Travel articles directory |
| `/blog/<slug>/` | `blog:detail` | Blog article and reader comments |

### Authentication & Account Routes
| URL | View | Description |
|---|---|---|
| `/account/login/` | `accounts:login` | Sign-in page |
| `/account/signup/` | `accounts:signup` | Registration form (initiates OTP flow) |
| `/account/verify-otp/` | `accounts:verify_signup_otp` | 6-digit registration code verification |
| `/account/forgot-password/` | `accounts:forgot_password` | Request password reset code |
| `/account/reset-password/` | `accounts:reset_password` | Submit code and set new password |
| `/account/resend-otp/` | `accounts:resend_otp` | Cooldown-protected OTP resend |
| `/account/redirect/` | `accounts:redirect` | Routes user to their role-specific dashboard |
| `/account/bookings/` | `accounts:bookings` | Customer's active and past bookings |
| `/account/bookings/<ref>/` | `accounts:booking_detail` | Roster traveler editor and guide chat |
| `/account/profile/` | `accounts:profile` | Customer profile management |

### Guide Portal Routes (`/guide/`)
| URL | Description |
|---|---|
| `/guide/` | Guide overview with upcoming assignments and KPIs |
| `/guide/bookings/` | Complete list of assigned departures |
| `/guide/bookings/<ref>/` | Trip manifest, roster, participant details |
| `/guide/bookings/<ref>/accept/` | Accept trip departure assignment |
| `/guide/bookings/<ref>/decline/` | Decline assignment (routes to admin queue) |
| `/guide/calendar/` | Interactive schedule calendar (FullCalendar) |
| `/guide/time-off/` | Log vacation or unavailability dates |
| `/guide/messages/` | Guide chat threads with travelers |
| `/guide/profile/` | Guide bio, language, and contact settings |

### Admin Dashboard Routes (`/dashboard/`)
| URL | Description |
|---|---|
| `/dashboard/` | Executive dashboard with analytics & charts |
| `/dashboard/tours/` | Tour catalogue management (create, update, toggle) |
| `/dashboard/destinations/` | Destination CRUD |
| `/dashboard/bookings/` | Master bookings table, status filter, CSV export |
| `/dashboard/bookings/needs-guide/` | Queue for unassigned/declined tours |
| `/dashboard/guides/` | Guide roster and performance metrics |
| `/dashboard/users/` | User role assignment (`customer`, `guide`, `admin`) |
| `/dashboard/reviews/` | Customer review moderation |
| `/dashboard/messages/` | Master view of customer-guide conversations |
| `/dashboard/inbox/` | Contact form inquiries inbox |
| `/dashboard/settings/` | No-code live theme & branding customizer |
| `/dashboard/chatbot-logs/` | Chatbot conversation audit logs |

---

## 7. Configuration Reference (`.env`)

Every system configuration option is controlled via `.env`:

```env
# --- Core Application --------------------------------------------------
DJANGO_SECRET_KEY=your-secure-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com

# --- AI Chatbot (Groq API) ---------------------------------------------
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODEL=llama-3.1-8b-instant
CHATBOT_MAX_MESSAGES_PER_HOUR=40

# --- Email Delivery (Gmail SMTP) ---------------------------------------
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_char_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
CONTACT_RECIPIENT_EMAIL=your_email@gmail.com

# --- Stripe Payments (Optional) ----------------------------------------
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd

# --- External Services (Optional) --------------------------------------
GOOGLE_MAPS_API_KEY=
```

---

## 8. Installation, Local Development & Testing

### 1. Setup Virtual Environment & Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your SMTP or Groq credentials
```

### 3. Initialize Database & Seed Demo Data
```bash
python manage.py migrate
python manage.py seed_demo_data
```

The seed script creates ready-to-test accounts:
- **Admin**: `admin` / `admin12345` (lands on `/dashboard/`)
- **Guide**: `guide` / `guide12345` (lands on `/guide/`)
- **Customer**: `customer` / `customer12345` (lands on `/account/bookings/`)

### 4. Running the Development Server
```bash
python manage.py runserver
```

### 5. Running the Test Suite
The project includes **109 automated tests** covering models, workflows, route security, and API endpoints:
```bash
python manage.py test
```

To run a specific test suite:
```bash
python manage.py test tests.test_routes_coverage
python manage.py test accounts.tests
```

---

## 9. Production Deployment Checklist & Security

When preparing the application for production deployment:

1. **Security Settings**:
   - Set `DJANGO_DEBUG=False` in `.env`.
   - Generate a strong cryptographic `DJANGO_SECRET_KEY`.
   - Set `DJANGO_ALLOWED_HOSTS` to your production domain(s).
   - Set `DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com`.
2. **Static & Media Files**:
   - Execute `python manage.py collectstatic --noinput`.
   - Serve `/static/` and `/media/` using Nginx, WhiteNoise, or AWS S3 / Cloudflare R2.
3. **Database**:
   - Migrate from SQLite to **PostgreSQL** by updating `DATABASES` in `config/settings.py`.
4. **Process Management**:
   - Run the application with **Gunicorn** or **Uvicorn** managed by systemd or Docker.
5. **SSL/TLS**:
   - Enable HTTPS via Let's Encrypt / Certbot.
   - Django automatically activates `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SECURE_CONTENT_TYPE_NOSNIFF` when `DEBUG=False`.
6. **Payment Webhooks**:
   - Point your Stripe production webhook endpoint to `https://yourdomain.com/payments/webhook/` and set `STRIPE_WEBHOOK_SECRET` in `.env`.
