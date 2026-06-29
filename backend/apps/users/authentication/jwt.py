from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.authentication import BaseAuthentication
from django.http import HttpRequest
from rest_framework import exceptions
from rest_framework_simplejwt.tokens import AccessToken


class CustomJWTAuthentication(BaseAuthentication):
    """
    Custom JWT Authentication that handles authentication properly
    """
    def authenticate(self, request):
        # Check if this is a public endpoint that should skip authentication
        # by checking the request path
        path = request.path
        
        # Public endpoints that should skip authentication
        public_endpoints = [
            '/api/users/register/',
            '/api/users/login/',
            '/api/users/password-reset-request/',
            '/api/users/password-reset/',
            '/api/users/verify-email/',
            '/api/users/resend-verification/'
        ]
        
        # If this is a public endpoint, skip authentication
        for endpoint in public_endpoints:
            if path.startswith(endpoint):
                return None
        
        # For other endpoints, check if Authorization header is present
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # If no Authorization header is present, return None to skip authentication
        if not auth_header:
            return None
        
        # If Authorization header is present, check if it's in Bearer format
        if not auth_header.startswith('Bearer '):
            return None
        
        # Extract the token from the header
        try:
            token = auth_header.split(' ')[1]  # Get token after 'Bearer '
        except IndexError:
            return None  # Malformed header
        
        # Attempt to decode and validate the JWT token
        try:
            # Create an AccessToken instance to validate the token
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token.get('user_id') or access_token.get('token_id')
            
            # Get the user from the database
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            return (user, token)  # Return user and token if valid
        except Exception:
            # If token is invalid, return None instead of raising exception
            # This allows the view's permission classes to handle it
            return None