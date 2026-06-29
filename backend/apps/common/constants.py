"""
App-wide constants for the lottery system.
"""

# Transaction Types
TRANSACTION_TYPES = {
    'TICKET_PURCHASE': 'Ticket Purchase',
    'PRIZE_AWARD': 'Prize Award',
    'DEPOSIT': 'Deposit',
    'WITHDRAWAL': 'Withdrawal',
    'REFUND': 'Refund',
    'ADMIN_ADJUSTMENT': 'Admin Adjustment',
    'REFERRAL_BONUS': 'Referral Bonus',
}

# Lottery Statuses
LOTTERY_STATUSES = {
    'DRAFT': 'Draft',
    'ACTIVE': 'Active',
    'CLOSED': 'Closed',
    'DRAWN': 'Drawn',
    'COMPLETED': 'Completed',
    'CANCELLED': 'Cancelled',
}

# Timezone Choices (common timezones)
TIMEZONE_CHOICES = [
    ('UTC', 'UTC'),
    ('America/New_York', 'Eastern Time (US & Canada)'),
    ('America/Chicago', 'Central Time (US & Canada)'),
    ('America/Denver', 'Mountain Time (US & Canada)'),
    ('America/Los_Angeles', 'Pacific Time (US & Canada)'),
    ('Europe/London', 'London'),
    ('Europe/Paris', 'Paris'),
    ('Europe/Berlin', 'Berlin'),
    ('Asia/Dubai', 'Dubai'),
    ('Asia/Kolkata', 'India'),
    ('Asia/Singapore', 'Singapore'),
    ('Asia/Tokyo', 'Tokyo'),
    ('Australia/Sydney', 'Sydney'),
]

# Notification Types
NOTIFICATION_TYPES = {
    'TICKET_PURCHASED': 'Ticket Purchased',
    'DRAW_RESULT': 'Draw Result',
    'WINNER': 'Winner',
    'WITHDRAWAL_STATUS': 'Withdrawal Status',
    'REFERRAL_BONUS': 'Referral Bonus',
    'LOTTERY_ENDING_SOON': 'Lottery Ending Soon',
    'SYSTEM': 'System Notification',
}

# Email Types
EMAIL_TYPES = {
    'WELCOME': 'welcome',
    'EMAIL_VERIFICATION': 'email_verification',
    'PASSWORD_RESET': 'password_reset',
    'TICKET_PURCHASE_CONFIRMATION': 'ticket_purchase_confirmation',
    'DRAW_RESULT_WIN': 'draw_result_win',
    'DRAW_RESULT_LOSS': 'draw_result_loss',
    'WITHDRAWAL_STATUS': 'withdrawal_status',
    'REFERRAL_BONUS_CREDITED': 'referral_bonus_credited',
    'LOTTERY_ENDING_SOON': 'lottery_ending_soon',
}

# Rate Limiting
RATE_LIMIT_LOGIN = '5/m'  # 5 requests per minute
RATE_LIMIT_REGISTER = '3/m'  # 3 requests per minute
RATE_LIMIT_PASSWORD_RESET = '3/h'  # 3 requests per hour
RATE_LIMIT_API = '100/m'  # 100 requests per minute

# Security
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_DURATION_MINUTES = 30
SESSION_TIMEOUT_HOURS = 24

# Lottery Defaults
DEFAULT_MAX_TICKETS_PER_USER = 10
DEFAULT_LOTTERY_TIMEZONE = 'UTC'

# Referral
REFERRAL_CODE_LENGTH = 12
REFERRAL_BONUS_EXPIRY_DAYS = 30

