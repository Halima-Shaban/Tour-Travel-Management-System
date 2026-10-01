# Admin dashboard (`/dashboard/`)

Available to users whose role is **Administrator** (and all superusers). Others get a 403.

## Overview
- **KPIs**: collected revenue (paid bookings) with month-over-month trend, total bookings, pending
  approvals, average rating, customer/guide counts.
- **Alerts** for active tours without a guide and unread contact messages.
- **Charts** (Chart.js, theme-aware): revenue + bookings over 12 months, booking status split,
  most-booked destinations.
- **Top tours by revenue**, **departures in the next 14 days** (with the assigned guide), latest bookings.

## Bookings
- Status chips with counts (pending / confirmed / completed / cancelled), search by reference,
  name, email or tour, filter by payment and upcoming/past.
- Row actions: confirm, mark completed, mark paid, cancel - one click.
- **Needs guide** tab: upcoming bookings without a guide or declined by one (also a red alert on the overview).
- Booking page: edit details · guide panel (response, decline reason, overlap warning, **assign/reassign**)
  · payment panel (amount, Stripe link, **refund via Stripe**) · participants · the trip **conversation**
  (reply as the office) · guide notes. Status/payment changes trigger the same notifications as the
  rest of the system.
- **Export CSV** respects the active filters.

## Catalogue
- **Tours**: create/edit/delete, assign a guide, sale price (validated to be lower than price),
  toggle active/featured inline. Tours with bookings can't be deleted (deactivate instead).
- **Destinations**: card grid with tour counts.
- **Reviews**: publish/hide or delete.

## People
- **Guides**: performance cards (tours, bookings, rating, availability); *Add guide* creates the
  login and guide profile in one step.
- **Users**: search/filter by role; edit role, contact info, guide details, or disable the account.
  You can't remove your own admin role.

## Engagement
- **Inbox** for contact-form messages (unread badge in the sidebar), reply by email.
- **Trip conversations** - every traveler ↔ guide chat; open one to reply as the office.
- **Chatbot logs** - every conversation, with which engine answered.
- **Notifications** bell: new bookings, guide accept/decline, payments, cancellations.
- **Subscribers** with CSV export. **Blog** CRUD.

## System
- **Customization** - see [customization.md](customization.md).
- **Django admin** (`/django-admin/`) remains available for low-level data access.
