# Hishably

**Digital credit ledger for wholesalers and distributors in Bangladesh.**

Most wholesalers still track credit (*baki*) in paper notebooks. Old dues get lost, sales reps collect cash with no clear record, and money gets stuck in the market.

Hishably replaces the paper *baki khata*. Wholesalers record every credit sale and payment, remind shops by SMS in Bangla, track what their sales reps collect, and always know how much money is owed to them.

This repository contains the backend API.

## Features

- **Phone login:** sign in with a mobile number and a one-time code
- **Multiple businesses:** one person can work in several businesses
- **Staff roles:** owner, manager, sales rep and accountant
- **Shops and areas:** group shops by route and set a credit limit for each
- **Ledger:** credit sales, payments, returns and discounts with a running balance
- **Payment methods:** cash, bKash, Nagad, bank transfer and cheque
- **Credit limit warning:** alerts when a sale goes over a shop's limit
- **Field collection:** daily rep routes, shop visits and end-of-day cash handover
- **SMS reminders:** automatic Bangla reminders before and after the due date
- **Shop link:** a secure page where a shop can see its own due
- **Reports:** dashboard, due aging and rep performance

## How money stays correct

- Every entry is saved safely, even when two people record at the same time
- Entries are never edited or deleted; mistakes are fixed with a reversal
- The same entry is never saved twice
- Every change is recorded with who made it and when
- Balances are rechecked every night

## Roles

| Role | Access |
| --- | --- |
| Owner | Full access |
| Manager | Shops, entries, reps and reports |
| Sales rep | Only shops in their own areas |
| Accountant | View only |

Each business's data is completely private from other businesses.

## Tech stack

- Django and Django REST Framework
- PostgreSQL
- Celery and Redis
- JWT authentication
- Docker

## Roadmap

- [ ] SMS gateway
- [ ] bKash, Nagad and SSLCommerz payments
- [ ] Subscription plans
- [ ] AI voice entry in Bangla
- [ ] Shop risk scores
- [ ] Web and mobile apps
