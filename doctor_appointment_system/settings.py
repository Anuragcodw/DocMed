"""
Django settings for doctor_appointment_system project.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'yy4&i60lnm&a)#t9y+2=u)=fs(r5r_if6mn7de&i=f7fvdtt%6',
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1,http://localhost,https://*.render.com,https://*.railway.app')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',') if origin.strip()]

# ---------------------------------------------------------------------------
# Feature Flags (API Safety Mode)
# ---------------------------------------------------------------------------
ENABLE_AI = os.environ.get('ENABLE_AI', 'True').lower() in ('true', '1', 'yes')
ENABLE_PAYMENTS = os.environ.get('ENABLE_PAYMENTS', 'True').lower() in ('true', '1', 'yes')
ENABLE_CHATBOT = os.environ.get('ENABLE_CHATBOT', 'True').lower() in ('true', '1', 'yes')
ENABLE_NOTIFICATIONS = os.environ.get('ENABLE_NOTIFICATIONS', 'True').lower() in ('true', '1', 'yes')
ENABLE_VIDEO = os.environ.get('ENABLE_VIDEO', 'True').lower() in ('true', '1', 'yes')
ENABLE_ANALYTICS = os.environ.get('ENABLE_ANALYTICS', 'True').lower() in ('true', '1', 'yes')


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Added for allauth

    # Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',

    # Django REST Framework (for JWT API endpoints)
    'rest_framework',
    'rest_framework_simplejwt',

    # Project apps
    'appointment',
    'accounts',
]

SITE_ID = 1

AUTH_USER_MODEL = 'accounts.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Added for allauth
]


# ---------------------------------------------------------------------------
# URL configuration
# ---------------------------------------------------------------------------

ROOT_URLCONF = 'doctor_appointment_system.urls'

WSGI_APPLICATION = 'doctor_appointment_system.wsgi.application'


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Override with DATABASE_URL if available (e.g. Heroku/production)
try:
    import dj_database_url

    db_from_env = dj_database_url.config(conn_max_age=600)
    if db_from_env:
        DATABASES['default'].update(db_from_env)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# ---------------------------------------------------------------------------
# Static files & Media
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'

STATICFILES_DIRS = [BASE_DIR / 'static']

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# ---------------------------------------------------------------------------
# Login redirect & Allauth config
# ---------------------------------------------------------------------------

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = [
    # Custom backend allowing login via username, email or phone
    'accounts.backends.MultiFieldBackend',
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
]

# NEW FLOW: Accounts are activated immediately on registration.
# Email verification is optional (encouraged via banner, not blocking).
# Doctors remain inactive until manually approved by admin.
EMAIL_VERIFICATION_REQUIRED = False

# Use 'optional' so allauth won't block login for unverified emails
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[DocMed] '
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = int(os.environ.get('EMAIL_CONFIRM_DAYS', 2))
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'

# ---------------------------------------------------------------------------
# Email Backend
# ---------------------------------------------------------------------------
# For local development, uses console backend (emails print to terminal).
# For production, set EMAIL_BACKEND to smtp and provide SMTP credentials
# via environment variables.
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'  # Change for production
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')       # Set in production env
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')  # Set in production env
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>')

# ---------------------------------------------------------------------------
# Allauth deprecated field compatibility
# ---------------------------------------------------------------------------
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1', 'password2']

# ---------------------------------------------------------------------------
# Social Account Config
# ---------------------------------------------------------------------------
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True          # Direct Google OAuth without intermediate page
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Social logins bypass email verification
SOCIALACCOUNT_QUERY_EMAIL = True           # Always fetch email from providers
SOCIALACCOUNT_EMAIL_REQUIRED = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'FETCH_USERINFO': True,
    },
    'github': {
        'SCOPE': ['user:email'],
    },
}

# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------
# Token expires after 24 hours (86400 seconds) by default.
# Override by setting PWD_RESET_TIMEOUT env variable.
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PWD_RESET_TIMEOUT', 86400))

# ---------------------------------------------------------------------------
# Security Hardening
# ---------------------------------------------------------------------------
# These flags are auto-enabled in production (when DEBUG=False).
# In local development they remain off to avoid HTTPS enforcement.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'

# ---------------------------------------------------------------------------
# Session Configuration
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = 86400 * 14   # 14 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ---------------------------------------------------------------------------
# Logging (production-ready)
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# ---------------------------------------------------------------------------
# Django REST Framework + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# Payment Gateways
# ---------------------------------------------------------------------------
# ⚠️  Set these in your .env file. NEVER hardcode API keys in source code.

# Razorpay (https://dashboard.razorpay.com/)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'YOUR_RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'YOUR_RAZORPAY_KEY_SECRET')
RAZORPAY_CURRENCY = os.environ.get('RAZORPAY_CURRENCY', 'INR')

# Stripe (https://dashboard.stripe.com/)
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'YOUR_STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'YOUR_STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'YOUR_STRIPE_WEBHOOK_SECRET')
STRIPE_CURRENCY = os.environ.get('STRIPE_CURRENCY', 'usd')

# UPI (No server-side API; uses QR code display)
UPI_ID = os.environ.get('UPI_ID', 'your_upi_id@bank')  # e.g. docmed@upi
UPI_MERCHANT_NAME = os.environ.get('UPI_MERCHANT_NAME', 'DocMed Healthcare')

# ---------------------------------------------------------------------------
# AI Report Analysis
# ---------------------------------------------------------------------------
# ⚠️  Get your free Gemini API key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')

# AI Analysis Feature flag (set to False to disable AI and use text extraction only)
AI_ANALYSIS_ENABLED = os.environ.get('AI_ANALYSIS_ENABLED', 'True').lower() in ('true', '1', 'yes')

# ---------------------------------------------------------------------------
# Notifications: SMS + WhatsApp (Twilio)
# ---------------------------------------------------------------------------
# ⚠️  Sign up at https://www.twilio.com/ and set these in your .env file.
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'YOUR_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'YOUR_TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '+1234567890')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# Enable/disable SMS and WhatsApp (set to False until Twilio is configured)
SMS_ENABLED = os.environ.get('SMS_ENABLED', 'False').lower() in ('true', '1', 'yes')
WHATSAPP_ENABLED = os.environ.get('WHATSAPP_ENABLED', 'False').lower() in ('true', '1', 'yes')

# ---------------------------------------------------------------------------
# Medical Report Upload Settings
# ---------------------------------------------------------------------------
MEDICAL_REPORT_MAX_SIZE_MB = int(os.environ.get('MEDICAL_REPORT_MAX_SIZE_MB', 10))
MEDICAL_REPORT_ALLOWED_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']

# ---------------------------------------------------------------------------
# Google Maps Integration
# ---------------------------------------------------------------------------
# ⚠️  Get your API key at https://console.cloud.google.com/
#     Enable: Maps JavaScript API, Geocoding API, Places API
#     Set GOOGLE_MAPS_API_KEY in your environment or .env file.
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# ---------------------------------------------------------------------------
# OCR & Poppler Configuration
# ---------------------------------------------------------------------------
POPPLER_PATH = os.environ.get('POPPLER_PATH', r"C:\Users\user\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin" if os.name == 'nt' else None)
TESSERACT_CMD = os.environ.get('TESSERACT_CMD', r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == 'nt' else None)