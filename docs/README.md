# GoTrip documentation

| Guide | What it covers |
|-------|----------------|
| **[Full System Documentation](FULL_DOCUMENTATION.md)** | **Complete end-to-end documentation across all modules, models, workflows, and APIs** |
| [Installation](installation.md) | Local setup, demo data, running tests |
| [Configuration](configuration.md) | Every `.env` variable |
| [Customization](customization.md) | Branding, theme, content and chatbot settings - no code needed |
| [Admin dashboard](admin-dashboard.md) | Everything an administrator can do |
| [Guide dashboard](guide-dashboard.md) | The tour guide's workspace |
| [Booking workflow](workflow.md) | How website, guide and admin connect: accept/decline, participants, time off, chat, notifications |
| [Payments](payments.md) | Stripe Checkout setup, webhook, refunds |
| [Chatbot](chatbot.md) | How the AI assistant works, Groq setup, offline mode |
| [Architecture](architecture.md) | Apps, models, roles, request flow - for developers |
| [Deployment](deployment.md) | Production checklist |

## Roles at a glance

| Role | Lands on after login | Can do |
|------|----------------------|--------|
| **Administrator** | `/dashboard/` | Everything: catalogue, bookings, people, content, customization |
| **Tour guide** | `/guide/` | See *only* their assigned bookings, accept/decline trips, manage time off, participants & manifests, chat with travelers |
| **Customer** | `/account/bookings/` | Book & pay (Stripe), add traveler names, chat with the guide, track/cancel bookings, write reviews |

Roles live on `accounts.Profile.role`. Superusers are always treated as administrators.
