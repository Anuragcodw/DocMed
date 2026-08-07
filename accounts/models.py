import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import pyotp

from accounts.managers import UserManager

GENDER_CHOICES = (
    ('male', 'Male'),
    ('female', 'Female'),
)

ROLE_CHOICES = (
    ('patient', 'Patient'),
    ('doctor', 'Doctor'),
)


class User(AbstractUser):
    """
    Custom user model that uses email for authentication,
    but also contains username and phone number for multi-field login.

    Adds role-based access control (patient/doctor), gender, and
    phone number fields.
    """

    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        error_messages={
            'unique': 'A user with that username already exists.',
        },
    )

    role = models.CharField(
        max_length=12,
        choices=ROLE_CHOICES,
        error_messages={'required': 'Role must be provided'},
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        default='',
    )
    email = models.EmailField(
        unique=True,
        blank=False,
        error_messages={
            'unique': 'A user with that email already exists.',
        },
    )
    phone_number = models.CharField(
        unique=True,
        blank=True,
        null=True,
        max_length=20,
        error_messages={
            'unique': 'A user with that phone number already exists.',
        },
    )
    # Firebase Cloud Messaging device token for push notifications
    # Updated via /api/save-fcm-token/ on each page load
    fcm_token = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        help_text='Firebase Cloud Messaging device/browser token for push notifications.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email


class OTPCode(models.Model):
    """
    Temporary table to store OTP codes sent for passwordless email login.
    Codes expire in 10 minutes.
    """
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.code}"


class EmailVerification(models.Model):
    """
    Model to store verification tokens for new user accounts.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        # Tokens are valid for 24 hours
        return timezone.now() > self.created_at + timezone.timedelta(hours=24)

    def __str__(self):
        return f"{self.user.email} - {'Verified' if self.is_verified else 'Pending'}"


class PhoneOTP(models.Model):
    """
    Model to store TOTP secrets and rate-limiting limits for phone OTP login.
    """
    phone_number = models.CharField(max_length=20, unique=True)
    otp_secret = models.CharField(max_length=32, default=pyotp.random_base32)
    attempts = models.IntegerField(default=0)
    last_sent = models.DateTimeField(auto_now=True)
    blocked_until = models.DateTimeField(null=True, blank=True)

    def is_blocked(self):
        if self.blocked_until and self.blocked_until > timezone.now():
            return True
        return False

    def __str__(self):
        return f"{self.phone_number} - Secret: {self.otp_secret}"


