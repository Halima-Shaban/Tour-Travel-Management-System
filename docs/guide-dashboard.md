# Guide dashboard (`/guide/`)

For users with the **Tour guide** role. A guide only ever sees tours assigned to them and bookings
on those tours - every query is scoped by `tour__guide=request.user`, and other records return 404.

| Page | What it does |
|------|--------------|
| **Overview** | Next departure card (travelers, duration, status, quick links), KPIs (upcoming bookings & travelers, awaiting confirmation, completed trips, rating), travelers-per-month chart, this week's trips, upcoming bookings, latest reviews |
| **Schedule** | FullCalendar month/list view of all trips, colour-coded by status, each spanning the tour's duration |
| **Travelers & bookings** | Upcoming / past / all, filter by status. Open a booking to see contact details and special requests, **confirm or complete** it and keep private **guide notes** (visible to admins). Cancellations are reserved for the office |
| **My tours** | Assigned tours with upcoming departures, traveler totals and rating |
| **Tour detail** | Each upcoming departure with seats filled vs. capacity, itinerary, inclusions |
| **Manifest** | Printable passenger list for one departure (`Print` hides the navigation) |
| **Reviews** | Average, star distribution and all reviews of the guide's tours |
| **My profile** | Name, photo, bio, languages, experience, availability - shown to travelers on tour pages |

Admins create guide accounts from **Dashboard → Guides → Add guide**, or promote an existing user
from **Users**.
