# Guide dashboard (`/guide/`)

For users with the **Tour guide** role. A guide only sees bookings assigned to them
(`Booking.guide`) - every query is scoped to `request.user`, and other records return 404.
See [workflow.md](workflow.md) for how this connects to the website and the admin dashboard.

| Page | What it does |
|------|--------------|
| **Overview** | New trip requests with one-click **Accept**, next departure card, KPIs (requests, upcoming trips & travelers, completed trips, rating), travelers-per-month chart, this week's trips and time off, latest reviews |
| **Schedule** | Calendar of requests (grey), confirmed and completed trips spanning each tour's duration, plus **time off** blocks. Add/remove time off - the website then refuses bookings for your tours on those dates, and you're warned if it overlaps accepted trips |
| **Trips & requests** | Tabs: Requests / Upcoming / Past / Declined / All. **Accept** (confirms the trip and notifies the traveler) or **Decline** with a reason (the office reassigns it). Overlap and time-off warnings before you accept |
| **Trip details** | Contact details, special requests, **participant list** (names, ages, nationality, dietary/medical notes), itinerary, **chat with the traveler**, private notes, *Mark completed* after the trip starts |
| **Messages** | All your trip conversations with unread badges |
| **My tours** | Assigned tours with upcoming departures, traveler totals and rating |
| **Tour detail** | Each upcoming departure with seats filled vs. capacity, itinerary, inclusions |
| **Manifest** | Printable passenger list for one departure, every named participant included |
| **Reviews** | Average, star distribution and all reviews of the guide's tours |
| **My profile** | Name, photo, bio, languages, experience, availability - shown to travelers on tour pages |

Admins create guide accounts from **Dashboard → Guides → Add guide**, or promote an existing user
from **Users**.
