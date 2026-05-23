# 🛎️ Click2Serve — Digital Service Hub

A two-sided web app for small-shop digital service providers (passport
applications, driving licences, bill payments, document services, etc.).
Customers book and track services from their phone; the shop owner runs
the queue, collects payments, and views revenue reports — all from one
deployable Streamlit app.

> **Live demo:** _coming once deployed to Streamlit Cloud — see "Deploy" below._

---

## What it does

### For customers
- Browse 12 pre-loaded services across 4 categories
- Filter by category, search by keyword
- Book a service, attach supporting documents, get an instant token number
- Track any booking by token number + mobile (lightweight privacy guard)

### For the shop owner
- Password-protected dashboard with today's KPIs
- Live bookings queue with one-click status updates
  (Pending → In Progress → Ready → Delivered → Cancelled)
- Mark payments as Cash / UPI / Card with the amount collected
- Revenue report: KPIs + daily bar charts + per-service breakdown + CSV export
- Change owner password from the dashboard

### Pre-loaded services
Government IDs · Passport · Aadhaar · PAN · Voter ID · Driving Licence ·
Vehicle Challan · Electricity / Gas / DTH · Photocopy / Print / Scan ·
Passport-size photos.

Add or edit anything via the SQLite DB or extend with a UI module.

---

## Tech stack

| Layer       | Choice                       |
| ----------- | ---------------------------- |
| UI          | Streamlit (multi-page nav)   |
| Database    | SQLite (file-based, zero ops)|
| Auth        | Salted SHA-256 password hash |
| File storage| Local `./uploads/` directory |
| Language    | Python 3.10+                 |

Why this stack: zero infrastructure cost, runs anywhere Python runs, can
be deployed on Streamlit Community Cloud for free, and ships in days
instead of weeks. When a paying client wants polish, the same data model
ports cleanly to a Next.js + Postgres deployment.

---

## Quick start

```bash
git clone https://github.com/<your-username>/click2serve.git
cd click2serve

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

Open http://localhost:8501.

### Default owner credentials

The very first run seeds an admin account:

- **Username:** `admin`
- **Password:** `click2serve123`

**Change it immediately** from Dashboard → "Change owner password".
(Defaults are only seeded when the `users` table is empty.)

---

## Deploy to Streamlit Cloud

1. Push this folder to a public GitHub repo (e.g. `click2serve`).
2. Sign in to https://share.streamlit.io with GitHub.
3. **New app** → pick repo → branch `main` → main file `app.py` → **Deploy**.
4. First build takes ~2 minutes. The app auto-redeploys on every push.

> Streamlit Cloud filesystem is **ephemeral** — uploaded documents and the
> SQLite DB are reset whenever the container restarts. For production use,
> swap `core/db.py` to point at a persistent Postgres (e.g. Supabase) and
> `save_document` to write to S3 / Supabase Storage.

---

## Project structure

```
click2serve/
├── app.py                       # Entry; st.navigation routes by auth state
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml              # Theme (Click2Serve blue + amber accent)
├── core/
│   ├── db.py                    # SQLite schema, CRUD, reports
│   ├── auth.py                  # Salted SHA-256 password auth
│   └── seed.py                  # 12 default services + admin user
├── pages/
│   ├── home.py                  # Customer landing + service grid
│   ├── book.py                  # Customer booking form (with file upload)
│   ├── track.py                 # Customer status lookup by token + phone
│   ├── login.py                 # Owner sign-in
│   ├── dashboard.py             # Owner KPIs + quick links + change password
│   ├── bookings.py              # Owner queue + status / payment updates
│   ├── revenue.py               # Owner reports + CSV export
│   └── logout.py
├── data/                        # SQLite DB lives here (gitignored)
└── uploads/                     # Customer documents (gitignored)
```

---

## Data model (high level)

```
services    ── id, name, category, description, govt_fee,
                service_charge, eta_hours, requirements, active
bookings    ── id, token, service_id, customer_name, customer_phone,
                customer_email, notes, status, payment_method,
                amount_paid, created_at, updated_at
documents   ── id, booking_id (FK), file_name, file_path, file_type,
                size_bytes, uploaded_at
users       ── id, username, password_hash, role, created_at
```

Indexes on `bookings.token`, `bookings.customer_phone`, `bookings.status`,
and `bookings.created_at` keep the queue and tracking views fast even at
thousands of rows.

---

## Roadmap (good first contributions)

- [ ] Service CRUD UI (currently DB-edit only)
- [ ] WhatsApp / SMS notification on status change
- [ ] Online payment via Razorpay / UPI deep links
- [ ] Multi-staff accounts with role-based permissions
- [ ] Receipt PDF auto-generated on payment
- [ ] Multi-language UI (Hindi + regional)
- [ ] Postgres + S3 backend for production
- [ ] Mobile-first redesign in Next.js

---

## Privacy and security notes

- All customer documents are stored on the server's local filesystem
  inside `./uploads/<booking_id>/`. They are never publicly served.
- Tracking requires both the token number **and** the mobile number used
  at booking — preventing token-guessing attacks.
- The default admin password is **deliberately weak** so the first-run
  setup is frictionless. Change it before exposing the app to the
  internet.
- For real production use: enable HTTPS (Streamlit Cloud does this
  automatically), rotate the password, and move the DB to managed
  Postgres so backups are someone else's problem.

---

## License

MIT — fork it, brand it, sell it to your local shop.
