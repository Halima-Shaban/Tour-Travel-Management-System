# Installation

Requirements: **Python 3.10+** (tested on 3.11). No Node/npm build step - CSS/JS are plain files, and
Bootstrap 5, Bootstrap Icons, Chart.js and FullCalendar load from the jsDelivr CDN.

```bash
git clone <repo-url> && cd Tour-Travel-Management-System
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit - at minimum set GROQ_API_KEY for the AI chatbot
python manage.py migrate
python manage.py seed_demo_data    # optional: realistic demo content
python manage.py runserver
```

Open http://127.0.0.1:8000.

## Demo accounts (created by `seed_demo_data`)

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin12345` |
| Guide | `guide` (also `layla`, `mehmet`, `sofia`) | `guide12345` |
| Customer | `customer` (and 9 others) | `customer12345` |

The seeder is idempotent (safe to re-run). `--flush` wipes tours/bookings/posts first.
**Change or delete these accounts before going live.**

## Running the tests

```bash
python manage.py test tests
```

The suite (29 tests) covers public pages, booking rules (sale price, capacity, past dates), role
isolation between admin / guide / customer, dashboard CRUD, customization and the chatbot
(Groq call mocked, offline fallback, rate limiting).
