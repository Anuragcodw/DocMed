# DocMed Appointment Reminder Setup Guide

## 📋 Overview: Two Scheduling Options

DocMed supports two modes for running automatic appointment reminders (24h + 2h):

| Mode | Infra Needed | Best For |
|---|---|---|
| **APScheduler** (built-in) | None — runs inside Django | Render Free, simple deployments |
| **Celery + Redis** | Redis server required | Production, high-traffic |

Both modes call the same command: `python manage.py send_appointment_reminders`

---

## ✅ Option A: APScheduler (Zero Infrastructure — Starts Automatically)

No setup needed. Once deployed, the scheduler starts automatically with Gunicorn.

```bash
# Starts automatically — no extra commands needed
gunicorn doctor_appointment_system.wsgi:application
```

The scheduler runs `send_appointment_reminders` **every 15 minutes** inside the web process.

To disable it, add to `.env`:
```
DISABLE_SCHEDULER=True
```

---

## 🚀 Option B: Celery + Redis (Production-Grade)

### Step 1 — Add Redis URL to .env
```env
REDIS_URL=redis://localhost:6379/0
# On Render: use the Internal Redis URL from your Redis instance
# e.g. REDIS_URL=rediss://red-abc123:6379
```

### Step 2 — Run database migrations for Celery Beat
```bash
python manage.py migrate
```

### Step 3 — Start Celery Worker (Terminal 1)
```bash
celery -A doctor_appointment_system worker --loglevel=info
```

### Step 4 — Start Celery Beat Scheduler (Terminal 2)
```bash
celery -A doctor_appointment_system beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### On Render — Add to render.yaml or Procfile
```yaml
# render.yaml
services:
  - type: worker
    name: celery-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A doctor_appointment_system worker --loglevel=info

  - type: worker
    name: celery-beat
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A doctor_appointment_system beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 🔧 Manual Test
```bash
python manage.py send_appointment_reminders
# Output: Successfully processed appointment reminders.
```

---

## 📌 What Reminders Send

For each approved appointment coming up in **24 hours** or **2 hours**:

| Channel | Patient | Doctor |
|---|---|---|
| Email | ✅ | ✅ |
| SMS (Twilio) | ✅ | ✅ |
| FCM Push | ✅ | — |

Reminder includes: Doctor name, patient name, date, time, hospital, and Google Meet link (if online).

**Deduplication**: `NotificationLog` prevents duplicate reminders for the same appointment within the same window.
