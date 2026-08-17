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

csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1,http://localhost,https://docmed-fx0m.onrender.com,https://*.render.com,https://*.railway.app')
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

    # Django REST Framework (for JWT API endpoints)
    'rest_framework',
    'rest_framework_simplejwt',

    # API Documentation (Swagger/ReDoc)
    'drf_spectacular',

    # Celery Beat — DB-backed periodic task scheduler
    'django_celery_beat',

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
                'appointment.context_processors.user_notifications',
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Local development: SQLite (no DATABASE_URL needed)
# Production (Render): PostgreSQL via DATABASE_URL environment variable
#
# On Render, set DATABASE_URL to your PostgreSQL Internal/External URL.
# Format: postgres://USER:PASSWORD@HOST:PORT/DBNAME
# ---------------------------------------------------------------------------

import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    # Production: PostgreSQL on Render with SSL and connection pooling
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        )
    }
else:
    # Local development: SQLite fallback
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


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
    # Render (and most PaaS) terminate SSL at the load balancer/proxy.
    # This tells Django to trust the X-Forwarded-Proto header from the proxy,
    # so it knows the original request was HTTPS.
    # WITHOUT this: SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE break admin login
    # because Django thinks the request is HTTP and refuses to set secure cookies.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
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
# AI Report Analysis & Chatbot
# ---------------------------------------------------------------------------
# ⚠️  Get your free Gemini API key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
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
# Google Calendar & Google Meet OAuth 2.0 Integration
# ---------------------------------------------------------------------------
# ⚠️  Configure in Google Cloud Console: https://console.cloud.google.com/
#     Enable: Google Calendar API
#     Authorized Redirect URI: https://docmed-fx0m.onrender.com/api/google/calendar/callback/
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get(
    'GOOGLE_REDIRECT_URI',
    'https://docmed-fx0m.onrender.com/api/google/calendar/callback/'
)
GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')


# ---------------------------------------------------------------------------
# OCR & Poppler Configuration
# ---------------------------------------------------------------------------
POPPLER_PATH = os.environ.get('POPPLER_PATH', r"C:\Users\user\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin" if os.name == 'nt' else None)
TESSERACT_CMD = os.environ.get('TESSERACT_CMD', r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == 'nt' else None)

# ---------------------------------------------------------------------------
# Firebase Authentication Configuration
# ---------------------------------------------------------------------------
FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY', '')
FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN', '')
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', '')
FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET', '')
FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID', '')
FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID', '')
FIREBASE_MEASUREMENT_ID = os.environ.get('FIREBASE_MEASUREMENT_ID', '')
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON', '')
FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', '')

# Firebase Cloud Messaging (FCM) Push Notifications
# ⚠️  Requires FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH above.
# Set FCM_ENABLED=True once credentials are configured.
FCM_ENABLED = os.environ.get('FCM_ENABLED', 'False').lower() in ('true', '1', 'yes')
FIREBASE_VAPID_PUBLIC_KEY = os.environ.get('FIREBASE_VAPID_PUBLIC_KEY', '')

# ---------------------------------------------------------------------------
# ElevenLabs Text-to-Speech (TTS) Configuration
# ---------------------------------------------------------------------------
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')

# ---------------------------------------------------------------------------
# Google Calendar + Google Meet Integration
# ---------------------------------------------------------------------------
# ⚠️  Enable the Google Calendar API in Google Cloud Console.
# Create a Service Account key and set GOOGLE_SERVICE_ACCOUNT_JSON in .env.
# Set GOOGLE_CALENDAR_ID to the calendar email (e.g. doctor@gmail.com or 'primary').
GOOGLE_CALENDAR_ENABLED = os.environ.get('GOOGLE_CALENDAR_ENABLED', 'False').lower() in ('true', '1', 'yes')
GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '')
GOOGLE_SERVICE_ACCOUNT_PATH = os.environ.get('GOOGLE_SERVICE_ACCOUNT_PATH', '')

# Public URL of this site (used in calendar event descriptions & FCM deep links)
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# ---------------------------------------------------------------------------
# ElevenLabs Text-to-Speech
# ---------------------------------------------------------------------------
# ⚠️  Get your API key at https://elevenlabs.io/
# Rachel voice (21m00Tcm4TlvDq8ikWAM) is recommended for medical applications.
ELEVENLABS_ENABLED = os.environ.get('ELEVENLABS_ENABLED', 'False').lower() in ('true', '1', 'yes')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
ELEVENLABS_MODEL_ID = os.environ.get('ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2')

# ---------------------------------------------------------------------------
# Google Cloud Translation API (Multi-Language)
# ---------------------------------------------------------------------------
# ⚠️  Enable Cloud Translation API in Google Cloud Console.
# Supports 12 languages: EN, HI, BN, TE, MR, TA, GU, KN, ML, PA, UR, OR
GOOGLE_TRANSLATE_ENABLED = os.environ.get('GOOGLE_TRANSLATE_ENABLED', 'False').lower() in ('true', '1', 'yes')
GOOGLE_TRANSLATE_API_KEY = os.environ.get('GOOGLE_TRANSLATE_API_KEY', '')

# ---------------------------------------------------------------------------
# API Documentation (drf-spectacular / Swagger + ReDoc)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'DocMed API',
    'DESCRIPTION': (
        'RESTful API for DocMed Doctor Appointment System. '
        'Covers appointments, payments, prescriptions, AI report analysis, '
        'video consultations, and push notifications.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'email': 'support@docmed.com'},
    'LICENSE': {'name': 'Proprietary'},
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
}

# ---------------------------------------------------------------------------
# Celery + Redis Background Task Queue
# ---------------------------------------------------------------------------
# ⚠️  REQUIRED: Install Redis on your server or use Render's Redis add-on.
#     Set REDIS_URL in .env  (e.g. redis://localhost:6379/0  or  rediss://...)
#     On Render: add a Redis instance and copy its Internal URL as REDIS_URL.
#
# START WORKERS (run these in separate terminal tabs):
#   celery -A doctor_appointment_system worker --loglevel=info
#   celery -A doctor_appointment_system beat   --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60  # 5 minutes max per task

# Celery Beat — Periodic Task Schedule
from celery.schedules import crontab as celery_crontab

CELERY_BEAT_SCHEDULE = {
    'send-appointment-reminders-every-15-mins': {
        'task': 'appointment.tasks.send_appointment_reminders_task',
        'schedule': celery_crontab(minute='*/15'),   # every 15 minutes
    },
}

# ---------------------------------------------------------------------------
# APScheduler Fallback (runs INSIDE Django/Gunicorn process)
# Active when Celery+Redis is NOT configured.
# Set DISABLE_SCHEDULER=True in .env to suppress it.
# ---------------------------------------------------------------------------
# No extra env vars needed — starts automatically on server launch.

# Python 3.14 + Django 4.2 Template Context Compatibility Patch
try:
    from django.template.context import BaseContext

    def _base_context_copy(self):
        duplicate = object.__new__(type(self))
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = _base_context_copy
except Exception:
    pass