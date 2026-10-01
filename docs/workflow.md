# Booking workflow & integration

How the website, the guide dashboard and the admin dashboard work on the same booking.
All state changes go through `tours/services.py`, which also sends the notifications.

```
Traveler books on the website
   │  booking.guide = tour's guide · guide_status = pending · status = pending
   │  → notify admins, the guide (email too) and the traveler
   ▼
Guide: Trips & requests ──► Accept ──► status = confirmed, traveler notified ("Your trip is confirmed")
                        └─► Decline (+reason) ──► admins notified, booking shows under "Needs guide"
                                                   │
Admin: Bookings → Needs guide → Reassign ──────────┘ new guide notified, must accept
   ▼
Traveler pays (Stripe) ──► payment_status = paid → admins, guide, traveler notified
   ▼
Trip day → guide marks completed → traveler can review the tour
Cancellation (traveler or office) → everyone involved is notified; refund from the admin page
```

| Concept | Where it lives | Who sees / edits it |
|---------|----------------|---------------------|
| Assigned guide & response | `Booking.guide`, `guide_status`, `guide_decline_reason` | Guide responds · admin reassigns · traveler sees "Guide confirmed" |
| Participants | `tours.Participant` | Traveler adds names on their booking page · guide sees them in trip details and the printable manifest · admin sees them |
| Time off | `tours.GuideUnavailability` | Guide manages it under **Schedule** · the website refuses bookings for that guide's tours on those dates · shown on the guide calendar |
| Conflicts | `services.guide_conflicts()` | Guide and admin get a warning when a trip overlaps another accepted trip |
| Trip chat | `messaging.Thread` (one per booking) / `Message` | Traveler, assigned guide and admins. Live updates via polling (5 s); unread badges |
| Notifications | `notifications.Notification` | Bell menu on the website and both dashboards; each links to the right page for that user's role |
| Payment | `Booking.payment_status`, Stripe ids | See [payments.md](payments.md) |

## Messaging details
- Endpoints: `GET /messages/<reference>/?after=<id>` (poll, marks read) and
  `POST /messages/<reference>/send/` (`{"body": "..."}`). Both require login and a participant/admin.
- Inboxes: traveler `/account/messages/`, guide `/guide/messages/`, admin `/dashboard/conversations/`.
- Polling keeps the stack simple (no Redis/WebSockets). For high traffic, swap `static/js/thread.js`
  to Django Channels without changing the models.
