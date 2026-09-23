# Hishably — backend

Credit (baki) management for wholesalers and distributors in Bangladesh.
Django 5 + Django REST Framework, PostgreSQL, Redis, Celery.

## Run it (Windows, PyCharm terminal)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # leave DB_NAME empty to use SQLite at first
python manage.py migrate
python manage.py seed_demo      # demo business with 12 shops, 3 reps, 2 months of history
python manage.py createsuperuser  # optional, for /admin (log in with phone)
python manage.py runserver
```

- API docs (Swagger): http://127.0.0.1:8000/api/docs/
- Admin: http://127.0.0.1:8000/admin/
- Tests: `pytest`

With Docker (PostgreSQL + Redis + Celery worker + beat): `docker compose up --build`,
then `docker compose exec web python manage.py seed_demo`.

## Log in (dev)

1. `POST /api/v1/auth/otp/send/` with `{"phone": "01711-000111"}`. In dev (`OTP_DEBUG=True`) the code
   comes back as `debug_code` and is printed in the console.
2. `POST /api/v1/auth/otp/verify/` with `{"phone": "01711-000111", "code": "123456"}` → `access` + `refresh`.
3. Send `Authorization: Bearer <access>` on every request.
4. `GET /api/v1/businesses/` → take the `alias`. All business endpoints are under `/api/v1/b/<alias>/`.

## Apps

| App | What it does |
| --- | --- |
| `accounts` | Phone-number user, OTP login (hashed codes, 5-minute expiry, 5 attempts), JWT |
| `businesses` | Business (tenant), memberships, roles: owner / manager / rep / accountant |
| `common` | Base models, BD phone validation, `BusinessScopedMixin` (tenant isolation), `seed_demo` |
| `shops` | Areas/routes, shops, credit limits, status filters, share links |
| `ledger` | Append-only `LedgerEntry`, `services.post_entry` / `reverse_entry`, audit log, public ledger |
| `collections` | Rep route, visits (with payment), end-of-day cash handover + confirmation |
| `notifications` | Bangla SMS templates, SMS log, reminder rules, provider interface, Celery tasks |
| `reports` | Dashboard, aging report, rep performance |

## Money rules (don't break these)

- Every change to money goes through `apps/ledger/services.py`.
- Posting locks the shop row (`select_for_update`) inside `transaction.atomic()`.
- Entries are never edited or deleted. Mistakes are fixed with a reversal entry (`POST entries/<id>/reverse/`).
- `Idempotency-Key` header on `POST entries/` stops double posting on retries.
- `Shop.current_balance` is a cache. The nightly `recalc_balances` task rebuilds it from the ledger and logs mismatches.
- Reps cannot push a shop over its credit limit; owners and managers can (that counts as approval).

## Endpoints (all under `/api/v1/`)

| Screen in the design | Endpoint |
| --- | --- |
| Login | `auth/otp/send/`, `auth/otp/verify/`, `auth/token/refresh/`, `auth/me/` |
| Business switcher / Settings | `businesses/`, `b/<alias>/` |
| Staff & roles | `b/<alias>/members/`, `b/<alias>/members/<id>/` |
| Dashboard | `b/<alias>/dashboard/?days=14` |
| Shops | `b/<alias>/areas/`, `b/<alias>/shops/?status=overdue&area=1&search=rahman&ordering=-current_balance` |
| Shop detail | `b/<alias>/shops/<shop>/`, `b/<alias>/shops/<shop>/ledger/` |
| New entry / Reverse | `b/<alias>/entries/` (GET, POST), `b/<alias>/entries/<id>/reverse/` |
| Share ledger | `b/<alias>/shops/<shop>/share-links/`, public: `public/ledger/<token>/` |
| Collections | `b/<alias>/reps/me/route/`, `b/<alias>/visits/`, `b/<alias>/handovers/`, `b/<alias>/handovers/<id>/confirm/` |
| Reports | `b/<alias>/reports/aging/`, `b/<alias>/reports/reps/` |
| Reminders & SMS | `b/<alias>/shops/<shop>/remind/`, `b/<alias>/sms/`, `b/<alias>/sms/templates/`, `b/<alias>/reminder-rules/` |

## Not built yet (next steps)

- Real SMS gateway: fill in `HttpSmsProvider` in `apps/notifications/providers.py` and set `SMS_PROVIDER=http`.
- bKash / Nagad / SSLCommerz payments + webhooks (`payments` app).
- Subscription billing and plan limits (`billing` app).
- AI voice entry, Bangla Q&A, risk scores (`ai` app).
- Next.js frontend (see `hishably-design.html` for every screen).
