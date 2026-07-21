# 🏥 DocMed — AI-Powered Doctor Appointment System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-4.2-green?style=for-the-badge&logo=django)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?style=for-the-badge&logo=mysql)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)
![Render](https://img.shields.io/badge/Deploy-Render-lightgrey?style=for-the-badge&logo=render)

**A full-featured healthcare platform with AI-powered medical report analysis, smart appointments, video consultations, and online payments.**

[Live Demo](#) • [Documentation](#table-of-contents) • [API Reference](#api-endpoints)

</div>

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment (Render)](#deployment-render)
- [API Endpoints](#api-endpoints)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### 🤖 AI & Machine Learning
| Feature | Description |
|---------|-------------|
| **Medical Report Analyzer** | Upload PDF/Image reports — AI extracts text and provides SUMMARY, FINDINGS, RECOMMENDATIONS |
| **AI Chat per Report** | Ask questions about your own medical report in plain language |
| **Symptom Checker** | Enter symptoms — AI suggests possible conditions and specialist to consult |
| **ML Risk Assessment** | Diabetes, Heart Disease, Stroke, Kidney Disease, BMI, Blood Pressure prediction |
| **Smart Search** | ML-enhanced report search with text preprocessing and classifier |
| **AI Prescription Summary** | Summarize complex prescriptions into plain English |
| **Doctor Recommender** | AI matches patients to the right specialist based on symptoms |

### 🗓️ Appointment Management
| Feature | Description |
|---------|-------------|
| **Booking Wizard** | Step-by-step appointment booking with doctor slot selection |
| **Real-time Availability** | API endpoint for live slot availability |
| **Approve/Reject/Reschedule** | Full booking lifecycle management |
| **Missed Appointment Tracking** | Auto-flag missed appointments |

### 💳 Payment System
| Gateway | Status |
|---------|--------|
| **Razorpay** | ✅ Integrated (configure keys in .env) |
| **Stripe** | ✅ Integrated (configure keys in .env) |
| **UPI** | ✅ Manual confirmation flow |
| **Invoice PDF** | ✅ Auto-generated on payment success |
| **Refund Management** | ✅ Admin-controlled refund workflow |

### 🎥 Video Consultations
- WebRTC-based in-browser video calls
- Meeting chat + file sharing
- Doctor notes during/after consultation

### 📋 Medical Reports
- Upload PDF, PNG, JPG reports (up to 10MB)
- AI-powered text extraction (pdfplumber for PDFs, Gemini Vision for images)
- Report history, search, filter by type
- Secure download (patient-owned only)

### 👨‍⚕️ Doctor Portal
- Comprehensive profile (qualifications, experience, clinic, documents)
- Vacation & availability management
- Slot management with API access
- Admin doctor verification workflow

### 🔒 Security
- Django AllAuth social login (Google, etc.)
- JWT API authentication (SimpleJWT)
- Custom security headers middleware
- Audit logging
- CSRF protection on all endpoints
- Rate limiting (configured via middleware)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, Django 4.2 |
| **Database** | MySQL 8.0 (SQLite in dev) |
| **AI/LLM** | Google Gemini 1.5 Flash |
| **ML** | scikit-learn, joblib, pdfplumber |
| **Auth** | Django AllAuth + SimpleJWT |
| **Payments** | Razorpay, Stripe |
| **Static/Media** | WhiteNoise, Cloudinary (optional) |
| **Frontend** | Bootstrap 5, Glassmorphism CSS, AOS |
| **Deployment** | Render (Gunicorn + WhiteNoise) |

---

## Architecture

```
DocMed/
├── doctor_appointment_system/   # Django project settings
│   ├── settings.py              # Main settings (reads from .env)
│   ├── urls.py                  # Root URL configuration
│   ├── wsgi.py                  # WSGI for Gunicorn
│   └── asgi.py                  # ASGI (WebSocket support)
│
├── accounts/                    # Auth, profiles (Patient + Doctor)
│   ├── models.py                # CustomUser, PatientProfile, DoctorProfile
│   ├── views.py                 # Login, register, profile
│   └── urls.py                  # /accounts/ routes
│
├── appointment/                 # Core appointment logic
│   ├── models.py                # Booking, Payment, Report, Prescription...
│   ├── views.py                 # Dashboard, admin views
│   ├── doctor_views.py          # Doctor profile & availability
│   ├── patient_views.py         # Patient profile & history
│   ├── booking_views.py         # Booking wizard, reviews
│   ├── payment_views.py         # Razorpay, Stripe, UPI
│   ├── prescription_views.py    # Prescription CRUD + PDF
│   ├── report_views.py          # Medical report upload + AI analysis
│   ├── ai_views.py              # AI Chat + Risk Assessment APIs
│   └── api_views.py             # REST API (nearby doctors etc.)
│
├── ai/                          # AI Service Layer
│   └── services/
│       ├── llm.py               # LLM manager (Gemini/OpenAI connectors)
│       ├── chatbot.py           # Conversational healthcare chatbot
│       ├── symptom_checker.py   # Symptom → condition analysis
│       ├── doctor_recommender.py # AI doctor matching
│       ├── prescription_summary.py # Prescription simplifier
│       ├── report_analyzer.py   # Report analysis pipeline
│       └── voice_assistant.py   # Voice/TTS assistant
│
├── ml_models/                   # ML Prediction Pipeline
│   ├── preprocessing.py         # Medical text preprocessor
│   ├── prediction.py            # Disease risk predictor
│   └── models_storage/          # Trained .pkl model files
│
├── services/                    # Supporting services
│   ├── enterprise/analytics.py  # Business analytics
│   ├── security/auth.py         # JWT + security helpers
│   ├── cloud/storage.py         # Cloudinary/S3 adapters
│   └── performance/cache.py     # Redis caching layer
│
├── templates/                   # All HTML templates
│   ├── base.html                # Base Glassmorphism layout
│   ├── 404.html / 500.html      # Custom error pages
│   ├── accounts/                # Login, register, profile templates
│   ├── appointment/             # Dashboard, booking, doctor templates
│   └── reports/                 # Medical report center templates
│
├── static/                      # Static assets
│   ├── style.css
│   ├── css/                     # design-tokens, glass, animations, theme
│   └── js/                      # booking wizard, report upload, AI chat
│
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── Procfile                     # Heroku/Render process configuration
├── render.yaml                  # Render deployment config
├── build.sh                     # Render build script
└── runtime.txt                  # Python version pin
```

---

## Installation

### Prerequisites
- Python 3.10+
- pip
- MySQL (or use SQLite for local dev — no configuration needed)
- Git

### Step 1: Clone the repository

```bash
git clone https://github.com/yourusername/doctor-appointment-system.git
cd doctor-appointment-system
```

### Step 2: Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

```bash
cp .env.example .env
# Edit .env with your settings (see Configuration section)
```

### Step 5: Run database migrations

```bash
python manage.py migrate
```

### Step 6: Create superuser

```bash
python manage.py createsuperuser
```

### Step 7: Train ML models (optional)

```bash
python ml_models/train.py
# Generates mock .pkl models in ml_models/models_storage/
```

### Step 8: Collect static files

```bash
python manage.py collectstatic --noinput
```

### Step 9: Run the development server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```env
# ── Django Core ──────────────────────────────────────
SECRET_KEY=your-super-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Database ─────────────────────────────────────────
# For SQLite (local dev — no setup needed):
DATABASE_URL=sqlite:///db.sqlite3

# For MySQL:
# DATABASE_URL=mysql://user:password@localhost:3306/docmed_db

# For PostgreSQL (Render):
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── AI Configuration ─────────────────────────────────
# Get free key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-1.5-flash
AI_ANALYSIS_ENABLED=False   # Set True after adding key

# ── Payment Gateways ─────────────────────────────────
# Razorpay — https://dashboard.razorpay.com/app/keys
RAZORPAY_KEY_ID=YOUR_RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET=YOUR_RAZORPAY_KEY_SECRET

# Stripe — https://dashboard.stripe.com/apikeys
STRIPE_PUBLISHABLE_KEY=YOUR_STRIPE_PUBLISHABLE_KEY
STRIPE_SECRET_KEY=YOUR_STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=YOUR_STRIPE_WEBHOOK_SECRET

# ── Email ─────────────────────────────────────────────
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# For real email (e.g., Gmail):
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_HOST_USER=you@gmail.com
# EMAIL_HOST_PASSWORD=your-app-password

# ── Media/Storage ─────────────────────────────────────
MEDICAL_REPORT_MAX_SIZE_MB=10
# For Cloudinary (production):
# CLOUDINARY_CLOUD_NAME=your-cloud
# CLOUDINARY_API_KEY=your-key
# CLOUDINARY_API_SECRET=your-secret

# ── Social Auth ───────────────────────────────────────
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
```

---

## Deployment (Render)

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/docmed.git
git push -u origin main
```

### Step 2: Create Render Web Service

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repository
3. Render will auto-detect `render.yaml`

### Step 3: Set Environment Variables in Render Dashboard

Set these under **Environment → Environment Variables**:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` |
| `DATABASE_URL` | Your PostgreSQL URL (use Render's free PostgreSQL) |
| `GEMINI_API_KEY` | Your Gemini key (optional) |
| `RAZORPAY_KEY_ID` | Your Razorpay key (optional) |

### Step 4: Deploy

Render will automatically run `build.sh` which:
1. Installs dependencies
2. Runs `collectstatic`
3. Runs migrations

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/token/` | Get JWT token pair | None |
| `POST` | `/api/token/refresh/` | Refresh JWT token | None |
| `GET` | `/api/doctors/nearby/` | Doctors by location | JWT |
| `GET` | `/api/doctors/<id>/slots/` | Doctor slot availability | JWT |
| `POST` | `/api/ai/chat/` | AI healthcare chatbot | Session |
| `POST` | `/api/ai/risk-assessment/` | ML disease risk prediction | Session |
| `POST` | `/reports/<id>/analyze/` | Trigger AI report analysis | Session |
| `POST` | `/reports/<id>/ask/` | Ask AI about a report | Session |

### AI Chat API Example

```bash
curl -X POST http://localhost:8000/api/ai/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "I have a persistent cough and fever for 3 days. What should I do?"}'
```

### Risk Assessment API Example

```bash
curl -X POST http://localhost:8000/api/ai/risk-assessment/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "diabetes",
    "age": 45,
    "bmi": 28.5,
    "glucose": 140,
    "blood_pressure": 85
  }'
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | — | Django secret key |
| `DEBUG` | ✅ | `True` | Enable debug mode |
| `DATABASE_URL` | ✅ | SQLite | Database connection string |
| `GEMINI_API_KEY` | Optional | — | Google Gemini AI key |
| `AI_ANALYSIS_ENABLED` | Optional | `False` | Enable AI report analysis |
| `RAZORPAY_KEY_ID` | Optional | — | Razorpay payment key |
| `RAZORPAY_KEY_SECRET` | Optional | — | Razorpay secret |
| `STRIPE_SECRET_KEY` | Optional | — | Stripe secret key |
| `MEDICAL_REPORT_MAX_SIZE_MB` | Optional | `10` | Max upload size |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ using Django • Bootstrap • Glassmorphism UI • Google Gemini AI

</div>
