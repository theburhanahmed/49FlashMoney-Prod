# 49FlashMoney - Project Guidelines

## Project Structure
- `backend/` - Django application (DRF, Channels, Celery)
- `frontend/` - React + TypeScript + Vite
- `docs/` - Product requirements documents

## Local Development Quick Start (no Redis/PostgreSQL needed)

```bash
# --- Backend (Terminal 1) ---
cd backend
python3 -m venv venv && source venv/bin/activate   # one-time
cp .env.example .env                                # one-time
pip install -r requirements.txt                     # one-time
python manage.py migrate                            # creates db.sqlite3
python manage.py createsuperuser                    # one-time
python manage.py runserver                          # http://localhost:8000

# --- Frontend (Terminal 2) ---
cd frontend
npm install                                         # one-time
npm run dev                                         # http://localhost:5173
```

Out of the box this uses:
- **SQLite** (file `backend/db.sqlite3`) -- no PostgreSQL install needed
- **In-memory cache** -- no Redis needed
- **In-memory channel layer** -- WebSockets work without Redis
- **Eager Celery** -- async tasks run synchronously in-process, no broker/worker needed
- **Console email** -- emails print to terminal instead of sending

### Optional: use Redis locally

If you have Redis running (`brew services start redis` / `docker run -p 6379:6379 redis`), set in `.env`:

```
REDIS_URL=redis://localhost:6379/0
```

The development settings will auto-detect this and switch to Redis for cache, channels, and Celery. You'll then need a Celery worker:

```bash
celery -A lottery worker -l info
celery -A lottery beat -l info      # optional, for scheduled tasks
```

### Seed sample data (optional)

```bash
python manage.py seed_data          # creates test users, lotteries, etc.
```

## Backend Commands (reference)

```bash
cd backend

# Run tests
python manage.py test apps.wallet
python manage.py test apps.games
python manage.py test

# Run all tests
python manage.py test

# Celery (only needed when REDIS_URL is set)
celery -A lottery worker -l info
celery -A lottery beat -l info
```

## Frontend Commands

```bash
cd frontend
npm install
npm run dev       # development server on http://localhost:5173
npm run build     # production build
npm run lint      # lint check
```

## Architecture Notes

- **Python 3.9+ compatible** - use `from __future__ import annotations` if you need PEP 604 union types (`X | Y`).
- **Business logic lives in service layers** (e.g., `apps/wallet/services.py`), NOT in views.
- **Views are thin** - they validate input and delegate to services.
- **Wallet uses an immutable ledger** - `LedgerEntry` records are never modified or deleted.
- **Idempotency** - all wallet mutations require idempotency keys to prevent duplicate processing.
- **Game engines** follow a formal ABC contract (`engines/base.py`): `initial_state(room, config)`, `apply_action(state, user_id, action, room_id, version)`, plus optional helpers (`get_public_state`, `is_finished`, `get_winners`, `validate_config`, `validate_bet`, `default_config`).
- **Game engine registry** (`engines/__init__.py`) dispatches to the correct engine by GameKind constant.
- **All game money movements go through WalletService** - `start_game` debits via ledger, `end_game` credits via ledger, with idempotency keys per room+player.
- **PaymentService** (`payments/payment_service.py`) orchestrates deposits and withdrawals through the wallet ledger with idempotency, reconciliation, and audit logging.
- **AuditService** (`users/audit_service.py`) provides centralised audit logging for all admin, financial, and security events.
- **Settings** are split: `base.py` (shared), `development.py`, `production.py`.

## Key Apps
- `apps.wallet` - Wallet & immutable ledger (source of truth for balances)
- `apps.games` - Game rooms, engines (Snakes & Ladders, Ludo, Carrom, Aviator, Wingo, Mines, Scratch Card), admin APIs
- `apps.slots` - Standalone slots games with provably fair RNG, SlotsService (ledger-integrated)
- `apps.payments` - Stripe + Razorpay integration, PaymentService (ledger-integrated)
- `apps.users` - Authentication, profiles, permissions, AuditService, ResponsibleGamingService
- `apps.notifications` - Email/push/WebSocket notifications, GameNotificationService, PaymentNotificationService
- `apps.promotions` - Promotion campaigns, claiming, bonus crediting via ledger
- `apps.vip` - VIP tiers, auto-promotion, cashback calculation via ledger
- `apps.analytics` - Financial/user/game metrics (GGR, NGR, RTP), CSV/Excel report exports
- `apps.lotteries` - Lottery draws, ticket purchases, winner selection
- `apps.referrals` - Referral tracking and bonus crediting

## Game Engine Architecture

Each engine module in `apps/games/engines/` must provide:
- `initial_state(room, config)` → dict
- `apply_action(state, user_id, action, room_id, version)` → dict

Optional ABC-compatible helpers (used by admin APIs and game orchestration):
- `game_kind()` → str
- `default_config()` → dict
- `is_finished(state)` → bool
- `get_winners(state)` → list[dict]
- `get_public_state(state)` → dict (strip secrets for client)
- `validate_config(config)` → list[str]
- `validate_bet(state, user_id, amount, action)` → str | None

## Admin API Endpoints
All require `IsAdminUser` permission:
- `GET /api/games/admin/engines/` - List registered engines
- `GET/PUT /api/games/admin/config/<game_kind>/` - Game configuration
- `POST /api/games/admin/maintenance/<game_kind>/` - Enable/disable games
- `GET /api/games/admin/rounds/` - Round history (filterable)
- `GET /api/games/admin/rounds/<room_id>/` - Round detail with full state
- `GET /api/games/admin/audit-logs/` - Audit log viewer (filterable)
- `GET /api/games/admin/withdrawals/` - Pending withdrawals
- `POST /api/games/admin/withdrawals/approve/` - Approve withdrawal
- `POST /api/games/admin/withdrawals/reject/` - Reject withdrawal

## Testing

Run all backend tests with:
```bash
cd backend && python manage.py test
```

Specific test suites:
```bash
python manage.py test apps.wallet                  # Wallet & ledger
python manage.py test apps.games                   # Game engines & rooms
python manage.py test apps.games.test_mines        # Mines engine
python manage.py test apps.games.test_scratch_card # Scratch Card engine
python manage.py test apps.games.test_admin_views  # Admin APIs
python manage.py test apps.payments.test_payment_service  # Payment flows
python manage.py test apps.slots                   # Slots service & API
python manage.py test apps.vip                     # VIP tiers & cashback
python manage.py test apps.promotions              # Promotions & claims
python manage.py test apps.analytics               # Analytics & game metrics
python manage.py test apps.notifications           # Notification services
```

## WebSocket Endpoints
- `ws/games/<room_id>/?token=<JWT>` – Game room (actions, state broadcast)
- `ws/notifications/?token=<JWT>` – Personal notification channel (events, mark-read)

## VIP API Endpoints
- `GET /api/vip/status/` – Current user's VIP status
- `GET /api/vip/tiers/` – All VIP tiers
- `POST /api/vip/cashback/` – Claim weekly cashback
- `POST /api/vip/admin/tiers/` – Create tier (admin)
- `PUT /api/vip/admin/tiers/<id>/` – Update tier (admin)
- `POST /api/vip/admin/tiers/set-tier/` – Manually set user tier (admin)

## Promotions API Endpoints
- `GET /api/promotions/promotions/` – List available promotions
- `POST /api/promotions/promotions/<id>/claim/` – Claim a promotion
- `GET /api/promotions/promotions/my-claims/` – User's claim history
- `POST /api/promotions/promotions/` – Create promotion (admin)

## Analytics API Endpoints (admin only)
- `GET /api/analytics/admin/analytics/dashboard/` – Overview metrics
- `GET /api/analytics/admin/analytics/financial/` – Financial metrics
- `GET /api/analytics/admin/analytics/games/` – Game KPIs (GGR, NGR, RTP)
- `GET /api/analytics/admin/analytics/charts/` – Time-series chart data
- `GET /api/analytics/admin/analytics/reports_financial/` – Download financial CSV

## Health & Readiness Endpoints (no auth required)
- `GET /api/health/` – Basic liveness probe
- `GET /api/health/db/` – Database connectivity check
- `GET /api/health/cache/` – Cache (Redis) connectivity check
- `GET /api/health/ready/` – Combined readiness probe (DB + cache + Celery + ledger spot-check)

## Production Hardening Rules

### Money-Moving Invariants
- **ALL balance mutations** must go through `WalletService.credit()` or `WalletService.debit()`.
- **Never call** `user.add_balance()` or `user.deduct_balance()` directly in production code.
  - Only exceptions: `users/admin_views.py` (admin manual override) and seed scripts.
- Every credit/debit **must** include a unique `idempotency_key` to prevent double-processing.
- Money-moving operations **must** be wrapped in `@transaction.atomic` or `with transaction.atomic():`.
- Balance checks **must** use `select_for_update()` to prevent race conditions.

### Views vs Services
- Views handle: request parsing, auth/permissions, responsible gaming checks, HTTP responses.
- Services handle: business logic, DB mutations, WalletService calls, audit logging.
- **Never put** balance operations, transaction creation, or bonus awarding directly in views.
