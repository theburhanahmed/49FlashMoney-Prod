# 49FlashMoney - Project Guidelines

## Project Structure
- `backend/` - Django application (DRF, Channels, Celery)
- `frontend/` - React + TypeScript + Vite
- `docs/` - Product requirements documents

## Backend Commands

```bash
cd backend

# Setup (first time)
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run tests
python manage.py test apps.wallet
python manage.py test apps.games
python manage.py test

# Run Celery worker
celery -A lottery worker -l info

# Run Celery beat scheduler
celery -A lottery beat -l info
```

## Frontend Commands

```bash
cd frontend

# Setup
npm install

# Run development server
npm run dev

# Build
npm run build

# Lint
npm run lint
```

## Architecture Notes

- **Business logic lives in service layers** (e.g., `apps/wallet/services.py`), NOT in views.
- **Views are thin** - they validate input and delegate to services.
- **Wallet uses an immutable ledger** - `LedgerEntry` records are never modified or deleted.
- **Idempotency** - all wallet mutations require idempotency keys to prevent duplicate processing.
- **Game engines** follow a standard interface: `initial_state(room, config)` and `apply_action(state, user_id, action, room_id, version)`.
- **Settings** are split: `base.py` (shared), `development.py`, `production.py`.

## Key Apps
- `apps.wallet` - Wallet & immutable ledger (source of truth for balances)
- `apps.games` - Game rooms and engines (Snakes & Ladders, Ludo, Carrom, Aviator, Wingo)
- `apps.payments` - Stripe + Razorpay integration
- `apps.users` - Authentication, profiles, permissions
- `apps.notifications` - Email/push notifications

## Testing

Run all backend tests with:
```bash
cd backend && python manage.py test
```

The wallet tests cover: balance correctness, idempotency, immutability, reconciliation, insufficient balance, frozen wallet, and admin adjustments.

The game engine tests cover: initial state generation, bet placement, cash-out logic, round resolution, and payout calculations for both Aviator and Wingo.
