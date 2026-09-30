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
- Full edit page with price breakdown, guide notes and customer account link.
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
- **Chatbot logs** - every conversation, with which engine answered.
- **Subscribers** with CSV export. **Blog** CRUD.

## System
- **Customization** - see [customization.md](customization.md).
- **Django admin** (`/django-admin/`) remains available for low-level data access.
