# Lottery System Backend - Django REST API

Complete Django REST Framework backend for the Lottery System with JWT authentication, user management, lottery administration, and transaction tracking.

**Full setup and env reference:** [docs/setup/SETUP.md](../docs/setup/SETUP.md) · [docs/setup/ENVIRONMENT_VARIABLES.md](../docs/setup/ENVIRONMENT_VARIABLES.md)

## Overview

The backend provides a robust REST API with:
- User authentication and authorization
- Lottery management system
- Ticket purchasing and management
- Wallet and transaction tracking
- Payment method management
- Withdrawal request system
- Admin functionalities
- Comprehensive error handling
- CORS support

## Technology Stack

- **Framework**: Django 4.2+
- **API**: Django REST Framework
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Database**: SQLite (development), PostgreSQL (production)
- **Python**: 3.8+
- **CORS**: django-cors-headers

## Project Structure

```
backend/
├── apps/
│   ├── lotteries/          # Lottery management app
│   │   ├── models.py       # Lottery & Ticket models
│   │   ├── views.py        # Lottery viewsets
│   │   ├── serializers.py  # Serializers
│   │   └── urls.py         # URL routing
│   ├── users/              # User management app
│   │   ├── models.py       # User extensions
│   │   ├── views.py        # User viewsets
│   │   ├── serializers.py  # Serializers
│   │   └── urls.py         # URL routing
│   └── transactions/        # Transaction tracking
│       ├── models.py       # Transaction model
│       ├── views.py        # Transaction viewsets
│       ├── serializers.py  # Serializers
│       └── urls.py         # URL routing
├── lottery/                 # Project config
│   ├── settings/           # Django settings package (base, database, logging)
│   ├── urls.py
│   └── wsgi.py
├── lotteryproject/          # Main project config
│   ├── urls.py             # Main URL routing
│   ├── settings.py         # Django settings
│   ├── wsgi.py             # WSGI config
│   └── asgi.py             # ASGI config
├── manage.py               # Django CLI
├── requirements.txt        # Python dependencies
├── db.sqlite3              # SQLite database
└── README.md               # This file
```

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### Setup Steps

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd lottery-system-demo
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   ```

3. **Activate Virtual Environment**
   ```bash
   # Linux/Mac
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create Superuser (Admin)**
   ```bash
   python manage.py createsuperuser
   ```
   Follow prompts to create admin account.

7. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

Server runs at: `http://localhost:8000`
Admin interface: `http://localhost:8000/admin`

## API Endpoints

### Authentication (8 endpoints)

#### User Registration
```
POST /api/users/register/
Body: {
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepass123",
  "password_confirm": "securepass123"
}
Response: {
  "token": "jwt_token",
  "user": { ... }
}
```

#### User Login
```
POST /api/users/login/
Body: {
  "username": "john_doe",
  "password": "securepass123"
}
Response: {
  "token": "jwt_token",
  "user": { ... }
}
```

#### Get Profile
```
GET /api/users/profile/
Headers: { "Authorization": "Bearer <token>" }
Response: { user profile data }
```

#### Add Funds
```
POST /api/users/add_funds/
Headers: { "Authorization": "Bearer <token>" }
Body: { "amount": 100.00 }
Response: { updated wallet data }
```

### Lotteries (13+ endpoints)

#### List All Lotteries
```
GET /api/lotteries/
Query Parameters:
  - status: ACTIVE, DRAWN, COMPLETED, CANCELLED
  - ordering: -created_at, -draw_date, etc.
Response: [ { lottery objects } ]
```

#### Get Lottery Details
```
GET /api/lotteries/{id}/
Response: { lottery data with statistics }
```

#### Create Lottery (Admin Only)
```
POST /api/lotteries/
Headers: { "Authorization": "Bearer <token>" }
Body: {
  "name": "Summer Jackpot",
  "description": "Big summer lottery",
  "ticket_price": 10.00,
  "prize_amount": 5000.00,
  "total_tickets": 1000,
  "draw_date": "2026-02-01T10:00:00Z",
  "status": "ACTIVE"
}
Response: { created lottery }
```

#### Buy Ticket
```
POST /api/lotteries/{id}/buy_ticket/
Headers: { "Authorization": "Bearer <token>" }
Body: { "quantity": 5 }
Response: { ticket confirmation }
```

#### Get Lottery Results
```
GET /api/lotteries/{id}/results/
Response: { winner information, prize details }
```

#### Conduct Draw (Admin Only)
```
POST /api/lotteries/{id}/draw/
Headers: { "Authorization": "Bearer <token>" }
Response: { draw results }
```

### Tickets (2 endpoints)

```
GET /api/tickets/              # List user's tickets
GET /api/tickets/{id}/         # Get ticket details
GET /api/lotteries/{id}/my_tickets/  # Get tickets for specific lottery
```

### Transactions (2 endpoints)

```
GET /api/transactions/              # List transactions
GET /api/transactions/summary/      # Get transaction summary
```

### Payment Methods (6 endpoints)

```
GET    /api/payment-methods/           # List methods
POST   /api/payment-methods/           # Add method
GET    /api/payment-methods/{id}/      # Get method
PUT    /api/payment-methods/{id}/      # Update method
DELETE /api/payment-methods/{id}/      # Delete method
POST   /api/payment-methods/{id}/set_primary/  # Set as primary
```

### Withdrawals (5 endpoints)

```
GET    /api/withdrawals/              # List withdrawals
POST   /api/withdrawals/              # Request withdrawal
GET    /api/withdrawals/{id}/         # Get withdrawal
POST   /api/withdrawals/{id}/approve/ # Approve (admin)
POST   /api/withdrawals/{id}/reject/  # Reject (admin)
```

## Database Models

### User Model
- Extends Django's built-in User model
- Additional fields: wallet_balance, is_verified
- Relationships: Profile, Tickets, Transactions

### Lottery Model
- name, description
- ticket_price, prize_amount
- total_tickets, available_tickets
- draw_date, status
- Relationships: Tickets, Participants

### Ticket Model
- lottery_id (FK)
- user_id (FK)
- ticket_number
- purchased_at
- is_winner, prize_amount

### Transaction Model
- user_id (FK)
- amount, type, status
- description
- created_at, updated_at

### Payment Method Model
- user_id (FK)
- name, type, account_number
- is_primary
- created_at, updated_at

### Withdrawal Model
- user_id (FK)
- amount, status
- payment_method_id (FK)
- created_at, updated_at

## Authentication

The API uses JWT (JSON Web Token) authentication.

### Token Usage

```bash
# 1. Get token from login
token=$(curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' | jq -r '.token')

# 2. Use token in authenticated requests
curl -X GET http://localhost:8000/api/users/profile/ \
  -H "Authorization: Bearer $token"
```

### Token Expiration
- Access token: 5 minutes (configurable)
- Refresh token: 7 days (configurable)

## Permissions

### Permission Classes
- `IsAuthenticated` - User must be logged in
- `IsAdmin` - User must be superuser
- `IsOwner` - User can only access their own data

### Protected Endpoints
- All endpoints under `/api/users/` require authentication
- All endpoints under `/api/lotteries/{id}/buy_ticket/` require authentication
- All admin operations require IsAdmin permission

## Settings Configuration

### Important Settings

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
]

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

## Management Commands

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell (interactive Python)
python manage.py shell

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test
# Or with pytest (see pytest.ini)
pytest

# Check for errors
python manage.py check

# Flush database (delete all data)
python manage.py flush

# Load test data
python manage.py loaddata fixture_name

# Export data
python manage.py dumpdata > backup.json

# Import data
python manage.py loaddata backup.json
```

## Testing

### Manual Testing with cURL

```bash
# Register user
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123"
  }'

# Login
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Get profile (requires token)
curl -X GET http://localhost:8000/api/users/profile/ \
  -H "Authorization: Bearer <your_token_here>"

# Create lottery (admin only)
curl -X POST http://localhost:8000/api/lotteries/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "name": "Test Lottery",
    "description": "A test lottery",
    "ticket_price": 10.00,
    "prize_amount": 1000.00,
    "total_tickets": 100,
    "draw_date": "2026-02-01T10:00:00Z",
    "status": "ACTIVE"
  }'
```

### Using Postman

1. Import API collection
2. Set environment variables:
   - `base_url` = http://localhost:8000/api
   - `token` = (auto-set from login response)
3. Create requests for each endpoint
4. Test all flows

## Troubleshooting

### Module Not Found
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Errors
```bash
# Reset database
python manage.py flush
python manage.py migrate

# Check for migration issues
python manage.py showmigrations
```

### Port Already in Use
```bash
# Use different port
python manage.py runserver 8001
```

### CORS Errors
- Check `CORS_ALLOWED_ORIGINS` in settings.py
- Verify frontend URL is in the list
- Ensure django-cors-headers is installed

### JWT Token Issues
- Token may have expired (get new one)
- Check token format in Authorization header
- Verify token in request headers

## Deployment

### Production Settings

```python
# settings.py
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

### Using Gunicorn

```bash
# Install
pip install gunicorn

# Run
gunicorn lotteryproject.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker

```bash
# Build image
docker build -t lottery-system .

# Run container
docker run -p 8000:8000 lottery-system
```

## Performance Optimization

### Database
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for many-to-many
- Add database indexes
- Use pagination

### Caching
- Enable Redis caching
- Cache API responses
- Cache database queries

### API
- Limit pagination to 10-20 items
- Implement rate limiting
- Compress responses
- Use CDN for static files

## Security Checklist

- [ ] Change SECRET_KEY for production
- [ ] Set DEBUG = False
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up HTTPS
- [ ] Configure CSRF protection
- [ ] Enable CORS only for trusted domains
- [ ] Use environment variables for sensitive data
- [ ] Regular security updates
- [ ] Implement rate limiting
- [ ] Add request logging
- [ ] Monitor for suspicious activity
- [ ] Regular database backups

## Support & Resources

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- JWT Guide: https://tools.ietf.org/html/rfc7519
- REST API Best Practices: https://restfulapi.net/

## License

MIT License

## Contributors

Burhan Ahmed

---

For detailed API documentation, see [docs/api/API_DOCUMENTATION.md](../docs/api/API_DOCUMENTATION.md)
For integration guide, see [docs/guides/INTEGRATION_GUIDE.md](../docs/guides/INTEGRATION_GUIDE.md)
