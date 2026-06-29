from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from datetime import datetime, date
from django.utils import timezone
from django.db.models import Q
from apps.users.models import User, UserProfile, AuditLog
from apps.common.validators import validate_password_strength


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_admin', 'wallet_balance', 'phone_number', 'is_verified',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'wallet_balance', 'created_at', 'updated_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, max_length=30, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, max_length=30, allow_blank=True, default='')
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    age_verification_consent = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 
                  'date_of_birth', 'age_verification_consent']

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email address")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Simplified password validation - just check minimum length
        # Remove complex requirements for easier registration
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        
        # Age verification - only check if date_of_birth is provided
        date_of_birth = data.get('date_of_birth')
        if date_of_birth:
            today = date.today()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            if age < 18:
                raise serializers.ValidationError({"date_of_birth": "You must be at least 18 years old to register"})
            # Auto-set age_verification_consent if user is 18+
            if age >= 18:
                data['age_verification_consent'] = True
        
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        age_verification_consent = validated_data.pop('age_verification_consent', False)
        
        # Set defaults for optional fields
        if not validated_data.get('first_name'):
            validated_data['first_name'] = ''
        if not validated_data.get('last_name'):
            validated_data['last_name'] = ''
        
        user = User.objects.create_user(**validated_data)
        user.role = 'user'  # Default role for new users
        user.is_active = True  # Auto-activate users
        user.email_verified = True  # Auto-verify email for easier registration
        # Set age verification if date_of_birth is provided and user is 18+
        if user.date_of_birth:
            today = date.today()
            age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))
            if age >= 18:
                user.age_verified = True
                user.age_verified_at = timezone.now()
        user.save()
        # Use get_or_create to avoid duplicate profile errors
        UserProfile.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Flexible login serializer that accepts either username or email.
    """
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password')

        if not username and not email:
            raise serializers.ValidationError("Username or email is required")

        identifier = username or email

        try:
            user = User.objects.get(Q(username__iexact=identifier) | Q(email__iexact=identifier))

            if user.is_account_locked():
                raise serializers.ValidationError("Account is locked due to multiple failed login attempts")

            authenticated_user = authenticate(username=user.username, password=password)

            if not authenticated_user:
                user.increment_failed_login_attempts()
                raise serializers.ValidationError("Invalid credentials")

            if not authenticated_user.is_active:
                raise serializers.ValidationError("Account is not active")

            user.reset_failed_login_attempts()
            user = authenticated_user

        except User.DoesNotExist:
            authenticate(username=identifier, password=password)
            raise serializers.ValidationError("Invalid credentials")

        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'total_spent', 'total_won', 'total_tickets_bought',
            'total_lotteries_participated', 'total_wins', 'avatar', 'bio'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_admin', 'role', 'wallet_balance', 'phone_number', 'date_of_birth',
            'address', 'city', 'country', 'is_verified', 'email_verified',
            'age_verified', 'age_verified_at', 'is_2fa_enabled', 'profile', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'wallet_balance', 'created_at', 'updated_at', 'email_verified', 'is_2fa_enabled']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add role-based permissions info
        data['permissions'] = {
            'is_user': instance.is_user,
            'is_moderator': instance.is_moderator,
            'is_super_admin': instance.is_super_admin,
        }
        return data


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'description', 'ip_address', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email address")
        return value

    def validate(self, data):
        email = data.get('email')
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise serializers.ValidationError("Account is not active")
        except User.DoesNotExist:
            # Don't reveal if email exists to prevent enumeration attacks
            pass
        return data


class PasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate(self, data):
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid or expired token"})
        
        if not user.password_reset_expires or user.password_reset_expires < datetime.now():
            raise serializers.ValidationError({"token": "Token has expired"})
        
        # Additional password validation
        if not any(c.isupper() for c in new_password):
            raise serializers.ValidationError({"new_password": "Password must contain at least one uppercase letter"})
        if not any(c.islower() for c in new_password):
            raise serializers.ValidationError({"new_password": "Password must contain at least one lowercase letter"})
        if not any(c.isdigit() for c in new_password):
            raise serializers.ValidationError({"new_password": "Password must contain at least one digit"})
        
        data['user'] = user
        return data


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        try:
            user = User.objects.get(email_verification_token=value)
            if user.email_verified:
                raise serializers.ValidationError("Email already verified")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid verification token")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_new_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_new_password')
        old_password = data.get('old_password')

        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match"})
        
        # Additional password validation
        if not any(c.isupper() for c in new_password):
            raise serializers.ValidationError({"new_password": "Password must contain at least one uppercase letter"})
        if not any(c.islower() for c in new_password):
            raise serializers.ValidationError({"new_password": "Password must contain at least one lowercase letter"})
        if not any(c.isdigit() for c in new_password):
            raise serializers.ValidationError({"new_password": "Password must contain at least one digit"})
        
        return data
