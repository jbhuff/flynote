# FlyNote ✈️

**Aircraft maintenance and airworthiness tracking for GA pilots who want to stay legal and fly with confidence.**

FlyNote is a self-hosted web application that tracks your aircraft's maintenance history, upcoming inspection due dates, Airworthiness Directive (AD) compliance, and component time/cycle limits — so you always know where your aircraft stands before you untie it.

Built by a Part 91 pilot and aircraft owner who got tired of spreadsheets.

---

## Why FlyNote?

Staying current on a GA aircraft involves juggling multiple overlapping requirements:

- **Annual inspection** — due 12 calendar months from the last annual
- **100-hour inspection** — required for hire operations, tracked by tach or Hobbs time
- **Airworthiness Directives** — recurring and one-time ADs with varying compliance intervals
- **Component time limits** — ELT batteries, transponder tests, altimeter/pitot-static checks, prop overhauls, and more

Most pilots track this in a logbook, a spreadsheet, or their memory. FlyNote puts it all in one place with clear due-date visibility and a full maintenance history.

---

## Features

- **Annual & 100-hr inspection tracking** — records dates, tach time, and performing A&P/IA
- **AD compliance log** — track one-time and recurring ADs by AD number, compliance date, and next-due interval
- **Component lifetime tracking** — configurable limits by hours, cycles, or calendar date for any installed component
- **Maintenance event history** — full log of all work performed with date, description, and who did it
- **Aircraft profile** — N-number, make/model, year, engine, prop, and avionics

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Django |
| Database | PostgreSQL |
| Web server | Nginx + Gunicorn |
| OS | Linux (Debian/Ubuntu) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip / virtualenv

### Installation

```bash
# Clone the repo
git clone https://github.com/jbhuff/flynote.git
cd flynote

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and secret key

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local dev, `False` in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |

---

## Data Model Overview

```
Aircraft
├── MaintenanceEvent (date, description, tach_time, performed_by)
├── InspectionRecord (type: annual/100hr, date, tach_time, ia_name)
├── ADCompliance (ad_number, description, compliance_date, next_due_date, next_due_hours)
└── Component (name, installed_date, installed_hours, limit_hours, limit_calendar_months)
```

---

## Regulatory Background

FlyNote is designed around FAA regulations applicable to Part 91 operations:

- **14 CFR §91.409** — Inspection requirements (annual, 100-hr)
- **14 CFR §91.417** — Maintenance records requirements
- **14 CFR §39** — Airworthiness Directives
- **14 CFR §91.411 / §91.413** — Altimeter/pitot-static and transponder test intervals

> **Disclaimer:** FlyNote is a recordkeeping aid, not a substitute for the official maintenance records required by 14 CFR §91.417. Always verify airworthiness with a certificated A&P mechanic or IA.

---

## Roadmap

- [ ] PDF export of maintenance history (for pre-buy inspections, ferry permits)
- [ ] Email/SMS reminders for upcoming due dates
- [ ] Multi-aircraft support
- [ ] REST API for third-party integrations
- [ ] Docker Compose for simplified self-hosting

---

## License

GPL v3 — see [LICENSE](LICENSE) for details.

---

## About the Author

Justin Huff is a software engineer and FAA-certificated private pilot based in South Carolina. He owns and flies a Piper PA-22 and built FlyNote out of a genuine need to track his own aircraft's airworthiness requirements more reliably than a spreadsheet allows.

- GitHub: [github.com/jbhuff](https://github.com/jbhuff)
- LinkedIn: [linkedin.com/in/justin-huff-sc](https://linkedin.com/in/justin-huff-sc)
