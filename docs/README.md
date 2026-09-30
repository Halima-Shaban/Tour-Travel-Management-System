# GoTrip documentation

| Guide | What it covers |
|-------|----------------|
| [Installation](installation.md) | Local setup, demo data, running tests |
| [Configuration](configuration.md) | Every `.env` variable |
| [Customization](customization.md) | Branding, theme, content and chatbot settings - no code needed |
| [Admin dashboard](admin-dashboard.md) | Everything an administrator can do |
| [Guide dashboard](guide-dashboard.md) | The tour guide's workspace |
| [Chatbot](chatbot.md) | How the AI assistant works, Groq setup, offline mode |
| [Architecture](architecture.md) | Apps, models, roles, request flow - for developers |
| [Deployment](deployment.md) | Production checklist |

## Roles at a glance

| Role | Lands on after login | Can do |
|------|----------------------|--------|
| **Administrator** | `/dashboard/` | Everything: catalogue, bookings, people, content, customization |
| **Tour guide** | `/guide/` | See *only* their assigned tours & bookings, confirm/complete trips, manifests, schedule, profile |
| **Customer** | `/account/bookings/` | Book tours, track/cancel bookings, write reviews |

Roles live on `accounts.Profile.role`. Superusers are always treated as administrators.
