from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User, UserProfile, AuditLog

User = get_user_model()


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        
        # Create test users
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPassword123',
            'password_confirm': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123',
            role='admin'
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)  # admin user + new user
        self.assertEqual(response.data['message'], 'User registered successfully')

    def test_user_registration_password_validation(self):
        """Test password validation during registration"""
        invalid_data = self.user_data.copy()
        invalid_data['password'] = 'weak'
        invalid_data['password_confirm'] = 'weak'
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', str(response.data).lower())

    def test_user_login_success(self):
        """Test successful user login"""
        # Register a user first
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Login with the registered user
        login_data = {
            'username': 'testuser',
            'password': 'TestPassword123'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_inactive_account(self):
        """Test login with inactive account"""
        user = User.objects.create_user(
            username='inactive_user',
            email='inactive@example.com',
            password='Password123',
            is_active=False
        )
        
        login_data = {
            'username': 'inactive_user',
            'password': 'Password123'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_audit_log_created_on_registration(self):
        """Test that audit log is created on user registration"""
        self.client.post(self.register_url, self.user_data, format='json')
        user = User.objects.get(username='testuser')
        audit_log = AuditLog.objects.filter(user=user, action='REGISTER').first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.description, 'User registered')

    def test_audit_log_created_on_login(self):
        """Test that audit log is created on user login"""
        # Register and login
        self.client.post(self.register_url, self.user_data, format='json')
        login_data = {
            'username': 'testuser',
            'password': 'TestPassword123'
        }
        self.client.post(self.login_url, login_data, format='json')
        
        user = User.objects.get(username='testuser')
        audit_log = AuditLog.objects.filter(user=user, action='LOGIN').first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.description, 'User logged in')


class UserViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123',
            role='user'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123',
            role='admin'
        )
        
        # Create JWT tokens for authentication
        refresh = RefreshToken.for_user(self.user)
        self.user_token = str(refresh.access_token)
        
        refresh_admin = RefreshToken.for_user(self.admin_user)
        self.admin_token = str(refresh_admin.access_token)

    def test_user_can_access_own_profile(self):
        """Test that user can access their own profile"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get('/api/users/users/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_user_cannot_access_other_users_list(self):
        """Test that regular user cannot access list of all users"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get('/api/users/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Regular users should only see their own profile
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'testuser')

    def test_admin_can_access_all_users_list(self):
        """Test that admin can access list of all users"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/users/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin should see all users
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_user_can_update_own_profile(self):
        """Test that user can update their own profile"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.put('/api/users/users/update_profile/', 
                                   {'first_name': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')

    def test_user_cannot_update_other_user_profile(self):
        """Test that user cannot update other user's profile"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='Password123'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.put(f'/api/users/users/{other_user.id}/', 
                                   {'first_name': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PasswordResetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.password_reset_request_url = reverse('password-reset-request')
        self.password_reset_url = reverse('password-reset')

    def test_password_reset_request(self):
        """Test password reset request"""
        data = {'email': 'test@example.com'}
        response = self.client.post(self.password_reset_request_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if user has a password reset token
        user = User.objects.get(email='test@example.com')
        self.assertIsNotNone(user.password_reset_token)

    def test_password_reset_with_valid_token(self):
        """Test password reset with valid token"""
        # Generate a reset token
        user = User.objects.get(username='testuser')
        token = user.generate_password_reset_token()
        
        data = {
            'token': token,
            'new_password': 'NewPassword123',
            'confirm_password': 'NewPassword123'
        }
        response = self.client.post(self.password_reset_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPassword123'))
        self.assertIsNone(user.password_reset_token)

    def test_password_reset_with_invalid_token(self):
        """Test password reset with invalid token"""
        data = {
            'token': 'invalid_token',
            'new_password': 'NewPassword123',
            'confirm_password': 'NewPassword123'
        }
        response = self.client.post(self.password_reset_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailVerificationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123',
            email_verified=False
        )
        self.email_verification_url = reverse('email-verification')
        self.resend_verification_url = reverse('resend-verification')

    def test_email_verification_with_valid_token(self):
        """Test email verification with valid token"""
        token = self.user.generate_verification_token()
        
        data = {'token': token}
        response = self.client.post(self.email_verification_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if email is now verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertIsNone(self.user.email_verification_token)

    def test_email_verification_with_invalid_token(self):
        """Test email verification with invalid token"""
        data = {'token': 'invalid_token'}
        response = self.client.post(self.email_verification_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_verification_email(self):
        """Test resending verification email"""
        data = {'email': 'test@example.com'}
        response = self.client.post(self.resend_verification_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if a new token was generated
        user = User.objects.get(email='test@example.com')
        self.assertIsNotNone(user.email_verification_token)