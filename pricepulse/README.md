# PricePulse — AI-Powered Dynamic Pricing & Demand Prediction Engine

PricePulse is a full-stack analytics platform for local small businesses (grocery
stores, bakeries, restaurants, cafes, clothing/electronics shops, pharmacies, salons,
etc.) that predicts product demand and recommends prices using a real, trained
machine learning model on top of the business's own historical sales data.

This is a working application, not a mockup: every dashboard number, chart, forecast
and price recommendation is computed from data in the database, and the ML metrics
(MAE / RMSE / R²) are calculated from an actual held-out test split — nothing is
hardcoded.

---

## 1. Features

- **AI demand forecasting** — RandomForestRegressor trained per business on real
  sales history (price, discounts, day-of-week, month, seasonality, holidays,
  category, lagged sales, moving averages, stock level).
- **Dynamic pricing engine** — transparent, rule-based recommendations on top of the
  ML prediction, with configurable max price increase/decrease limits and hard
  min/max price enforcement per product.
- **Price simulator** — drag a price slider and see model-estimated demand and
  revenue at that price, live.
- **Inventory intelligence** — days-of-cover, Healthy / Low / Critical / Overstocked
  status, and restocking recommendations.
- **Business alerts** — high demand, overstock risk, pricing opportunity, stockout
  risk.
- **CSV import** for historical sales, with row-level validation (missing values,
  bad dates, negative quantities, unknown SKUs) instead of crashing.
- **Analytics** — revenue trend, sales volume, category and product performance.
- **Full product CRUD**, sales management, authentication, and per-business data
  isolation.
- Light/dark mode, responsive layout, toasts, loading/empty states.

## 2. Architecture

```
pricepulse/
├── manage.py
├── config/                # Django project settings, root urls
├── businesses/             # Business model, auth views, dashboard pages
├── products/                # Product model + REST API
├── sales/                   # SalesRecord/Promotion/CompetitorPrice + CSV import
├── forecasting/              # DemandPrediction/ModelMetadata + ML pipeline
│   ├── services/
│   │   ├── features.py         # shared feature engineering (train + predict)
│   │   └── demand_predictor.py # loads model, predicts, estimates confidence
│   └── management/commands/train_demand_model.py
├── pricing/                  # PriceRecommendation + pricing engine
│   └── services/pricing_engine.py
├── inventory/                # derived inventory intelligence API
├── alerts/                   # BusinessAlert model + API
├── analytics/                 # revenue/category/product analytics API
├── templates/                 # server-rendered pages (landing, auth, dashboard)
├── static/{css,js}/           # design system CSS + vanilla JS (Fetch API, Chart.js)
└── ml_models/trained_models/  # joblib-serialized trained models (git-ignored)
```

The ML and pricing logic is intentionally kept out of Django views, in
`forecasting/services/` and `pricing/services/`, so it can be tested, reused, and
reasoned about independently of HTTP.

## 3. Technology stack

- **Backend:** Python 3, Django 6, Django REST Framework, MySQL (via Django ORM)
- **ML:** pandas, numpy, scikit-learn (RandomForestRegressor), joblib
- **Frontend:** HTML5, CSS3 (hand-built design system, no framework), vanilla
  JavaScript (Fetch API), Chart.js
- **Auth:** Django's built-in session authentication

## 4. Installation

### 4.1 Prerequisites
- Python 3.11+
- MySQL Server 8.x running locally (or accessible remotely)
- On Debian/Ubuntu, the MySQL client library headers are needed to build
  `mysqlclient`: `sudo apt-get install default-libmysqlclient-dev build-essential pkg-config`

### 4.2 Clone & set up a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 4.3 Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
DJANGO_SECRET_KEY=<generate a long random string>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=mysql            # or "sqlite" for a zero-config quick start

MYSQL_DATABASE=pricepulse
MYSQL_USER=pricepulse_user
MYSQL_PASSWORD=<your-password>
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

### 4.4 Create the MySQL database

```sql
CREATE DATABASE pricepulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pricepulse_user'@'localhost' IDENTIFIED BY '<your-password>';
GRANT ALL PRIVILEGES ON pricepulse.* TO 'pricepulse_user'@'localhost';
FLUSH PRIVILEGES;
```

(For a quick start without installing MySQL, set `DB_ENGINE=sqlite` in `.env`
instead — the whole app works identically on SQLite, just without a MySQL server.)

### 4.5 Migrate, seed, and train

```bash
python manage.py makemigrations
python manage.py migrate

# Creates a demo business ("Sunrise Bakery & Cafe"), 20 realistic Indian products,
# ~6 months of daily sales history, promotions, competitor prices, and alerts.
python manage.py seed_data
# -> prints a demo login: username `demo_owner`, password `PricePulse@123`

# Trains the RandomForestRegressor and prints real MAE / RMSE / R2 metrics.
python manage.py train_demand_model
```

### 4.6 Run the server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`, log in with the demo credentials above (or
register a new account, which will walk you through business onboarding), and
explore Overview → Products → Sales → Demand Forecast → Smart Pricing →
Inventory → Analytics → Alerts → AI Model.

## 5. Demo flow

1. Register (or log in as `demo_owner`).
2. New accounts are walked through a short business-profile onboarding form.
3. Add products, or use the seeded catalog.
4. Import historical sales via **Sales → Import Historical Sales** (CSV columns:
   `sku, sale_date, quantity_sold, selling_price[, discount_percentage]`).
5. Train (or retrain) the model from the **AI Model** page.
6. Open **Demand Forecast**, pick a product and horizon, see predicted demand,
   confidence, and a historical-vs-predicted chart.
7. Open **Smart Pricing**, review AI recommendations, click **Apply Price** and
   confirm in the modal — the product's price updates immediately.
8. Try the **Price Simulator**: drag the slider and watch estimated demand and
   revenue update live, computed by feeding a hypothetical price back into the
   same trained model.
9. Check **Inventory** for stock health and **Alerts** for demand/pricing/
   stockout signals.

## 6. API overview

All endpoints below live under `/api/` and require an authenticated session
(log in via the web UI first) except where noted.

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/api/products/` | List / create products |
| GET/PUT/DELETE | `/api/products/{id}/` | Retrieve / update / delete a product |
| GET/POST | `/api/sales/` | List / create sales records (filter by `product`, `from`, `to`) |
| POST | `/api/sales/import/` | CSV import (multipart `file` field) |
| GET | `/api/demand/forecast/?product=<id>&days=<7-30>` | Generate/refresh a demand forecast |
| POST | `/api/demand/predict/` | Same as above, JSON body `{product, days}` |
| POST | `/api/model/retrain/` | Retrain the ML model for the logged-in business |
| GET | `/api/pricing/recommendations/` | Generate price recommendations for all products |
| POST | `/api/pricing/simulate/` | What-if demand/revenue at a candidate price, body `{product, price}` |
| POST | `/api/pricing/apply/` | Apply a recommendation, body `{recommendation_id}` |
| GET | `/api/inventory/` | Derived inventory intelligence |
| GET | `/api/alerts/` | List alerts (`?unread=true` to filter) |
| POST | `/api/alerts/{id}/read/` | Mark an alert read |
| GET | `/api/analytics/revenue/?range=7d\|30d\|90d` | Revenue/units/category/top-product analytics |

Every business-scoped endpoint enforces that the logged-in user can only see and
modify data belonging to their own `Business`.

## 7. The ML pipeline

```
sales data (MySQL)
  → forecasting/services/features.py   (feature engineering, shared by train + predict)
  → train/test split
  → RandomForestRegressor (default: 200 trees, max_depth=12)
  → MAE / RMSE / R2 computed on the held-out test split
  → joblib.dump(...)                    (ml_models/trained_models/business_<id>_latest.joblib)
  → forecasting/services/demand_predictor.py (loads model, builds live feature row, predicts)
  → pricing/services/pricing_engine.py  (rule-based recommendation on top of the prediction)
```

Re-run training any time with `python manage.py train_demand_model` (optionally
`--business-id <id>` for a single business), or from the **AI Model** page in the
dashboard. A minimum of 30 sales records is required; below that, training is
skipped with an explicit message rather than producing a meaningless model.

Confidence scores shown alongside predictions are a heuristic (based on the
model's overall R² and the recent volatility of that specific product's sales),
not a formal statistical prediction interval — this is stated explicitly in code
comments and should be read as "how much to trust this number" rather than a
precise probability.

## 8. Pricing rules

Configurable via `.env` or `config/settings.py`:

- `PRICING_MAX_INCREASE_PCT` (default 20%)
- `PRICING_MAX_DECREASE_PCT` (default 25%)

Every recommendation is additionally clamped to the product's own
`minimum_price` / `maximum_price`, and an active promotion on a product prevents
the engine from stacking a further price increase on top of it.

## 9. Security notes

- Secrets (Django secret key, MySQL password) are read from `.env`, never
  hardcoded.
- CSRF protection is enabled Django-wide; the frontend's `ppFetch()` helper
  attaches the CSRF token automatically on non-GET requests.
- Passwords are hashed via Django's built-in password hashers and validated
  (minimum length, not too common, not fully numeric).
- Every business-scoped view filters querysets by `request.user.business`, so
  one business owner cannot see or modify another's data.
- CSV uploads are limited to 5MB and must have a `.csv` extension.

## 10. Known simplifications (be aware of these)

Given the size of the original spec, a few areas were intentionally simplified
rather than fully built out, to keep everything else genuinely working end to end:

- The **Promotions** and **Competitor Prices** models, seed data, and APIs exist
  in the database and are used by the pricing engine (active promotions suppress
  price increases), but there isn't yet a dedicated CRUD page for managing them
  in the UI — they can be managed via the Django admin at `/admin/`.
- **Price elasticity** as a standalone dedicated page (Section 39 of the original
  spec) was not built; the Price Simulator effectively surfaces the same
  price-vs-demand relationship interactively instead.
- The "is_holiday" feature uses a small fixed set of major Indian public holidays
  rather than a full regional holiday calendar.
- Confidence scores are an explicit heuristic (see Section 7 above), not a
  formal prediction interval — this is a modeling choice worth knowing about
  before presenting the numbers to a business owner as precise probabilities.

## 11. Running tests / sanity checks manually

```bash
python manage.py check
python manage.py test        # (no test suite is bundled yet — add app-level tests as needed)
```

The full flow (migrate → seed → train → forecast → recommend → simulate → apply
→ inventory → analytics → alerts → CSV import → data isolation between two
different business accounts) was manually verified via Django's test client
during development.

## 12. Future improvements

- Dedicated Promotions and Competitor Price management pages.
- Gradient Boosting / model comparison and automatic model selection.
- Scheduled/periodic retraining (e.g. via Celery beat) instead of manual trigger.
- Formal prediction intervals instead of the current confidence heuristic.
- Multi-user businesses (staff accounts with roles), not just one owner per
  business.
- Product photo uploads and richer product detail pages.
