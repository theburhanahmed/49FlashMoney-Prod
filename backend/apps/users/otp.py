"""
OTP utilities for two-factor authentication.
"""
import pyotp
import qrcode
import io
import base64
from django.conf import settings


def generate_totp_secret():
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def generate_totp_uri(user, secret):
    """
    Generate TOTP URI for QR code.
    
    Args:
        user: User instance
        secret: TOTP secret
    
    Returns:
        TOTP URI string
    """
    totp = pyotp.TOTP(secret)
    issuer_name = getattr(settings, 'OTP_ISSUER_NAME', 'Lottery System')
    return totp.provisioning_uri(
        name=user.email,
        issuer_name=issuer_name
    )


def generate_qr_code(uri):
    """
    Generate QR code image from URI.
    
    Args:
        uri: TOTP URI string
    
    Returns:
        Base64 encoded QR code image
    """
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp(secret, token):
    """
    Verify TOTP token.
    
    Args:
        secret: TOTP secret
        token: Token to verify
    
    Returns:
        True if token is valid, False otherwise
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def generate_backup_codes(count=10):
    """
    Generate backup codes for 2FA.
    
    Args:
        count: Number of backup codes to generate
    
    Returns:
        List of backup codes
    """
    import secrets
    import string
    
    codes = []
    for _ in range(count):
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        codes.append(code)
    
    return codes

