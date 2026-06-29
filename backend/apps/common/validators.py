"""
Custom validators for the lottery system.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
import re


def validate_age(date_of_birth, min_age=18):
    """
    Validate that user is at least min_age years old.
    
    Args:
        date_of_birth: date of birth
        min_age: minimum age (default: 18)
    
    Raises:
        ValidationError if age requirement not met
    """
    if date_of_birth is None:
        raise ValidationError('Date of birth is required.')
    
    today = timezone.now().date()
    age = (today - date_of_birth).days // 365
    
    if age < min_age:
        raise ValidationError(f'User must be at least {min_age} years old.')


def validate_password_strength(password):
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: password string
    
    Raises:
        ValidationError if password doesn't meet requirements
    """
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one digit.')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character.')


def validate_phone_number(phone_number):
    """
    Validate phone number format.
    
    Args:
        phone_number: phone number string
    
    Raises:
        ValidationError if phone number format is invalid
    """
    if not phone_number:
        return
    
    # Basic phone number validation (digits, spaces, dashes, parentheses, plus)
    pattern = r'^[\d\s\-\(\)\+]+$'
    if not re.match(pattern, phone_number):
        raise ValidationError('Invalid phone number format.')
    
    # Remove non-digit characters for length check
    digits_only = re.sub(r'\D', '', phone_number)
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError('Phone number must be between 10 and 15 digits.')


def validate_email_domain(email):
    """
    Validate email domain (basic check).
    
    Args:
        email: email address string
    
    Raises:
        ValidationError if email domain is invalid
    """
    if not email:
        return
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError('Invalid email format.')


def validate_positive_amount(amount):
    """
    Validate that amount is positive.
    
    Args:
        amount: decimal amount
    
    Raises:
        ValidationError if amount is not positive
    """
    if amount is None:
        raise ValidationError('Amount is required.')
    
    if amount <= 0:
        raise ValidationError('Amount must be greater than zero.')


def validate_lottery_dates(start_date, end_date, draw_date):
    """
    Validate lottery date logic.
    
    Args:
        start_date: lottery start date
        end_date: lottery end date
        draw_date: draw date
    
    Raises:
        ValidationError if dates are invalid
    """
    if start_date and end_date and start_date >= end_date:
        raise ValidationError('Start date must be before end date.')
    
    if end_date and draw_date and end_date >= draw_date:
        raise ValidationError('End date must be before draw date.')
    
    if start_date and draw_date and start_date >= draw_date:
        raise ValidationError('Start date must be before draw date.')

