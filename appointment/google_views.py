"""
Google Calendar OAuth & Calendar Sync Management Views.

Endpoints:
  - /api/google/calendar/connect/ (Doctor initiates OAuth)
  - /api/google/calendar/callback/ (OAuth callback URL configured in Google Console)
  - /api/google/calendar/disconnect/ (Doctor disconnects Calendar)
  - /api/google/calendar/sync-retry/<booking_id>/ (Admin or Doctor retries failed sync)
"""

import json
import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View

from appointment.decorators import doctor_required
from appointment.models import DoctorProfile, TakeAppointment
from appointment.google_calendar_service import (
    get_google_oauth_flow, create_google_calendar_event
)

logger = logging.getLogger(__name__)


class GoogleCalendarConnectView(LoginRequiredMixin, View):
    """
    Doctor Dashboard Action: Connect Google Calendar.
    Redirects doctor to Google OAuth 2.0 Consent Screen.
    """
    login_url = reverse_lazy('accounts:login')

    @method_decorator(doctor_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            flow = get_google_oauth_flow(
                redirect_uri=getattr(settings, 'GOOGLE_REDIRECT_URI', 'https://docmed-fx0m.onrender.com/api/google/calendar/callback/')
            )
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            request.session['google_oauth_state'] = state
            return redirect(authorization_url)
        except Exception as exc:
            logger.error(f'Failed to initiate Google OAuth flow: {exc}', exc_info=True)
            messages.error(request, 'Unable to connect Google Calendar. Please check GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET in settings.')
            return redirect('appointment:doctor-dashboard')


class GoogleCalendarCallbackView(View):
    """
    Google OAuth Callback Handler: https://docmed-fx0m.onrender.com/api/google/calendar/callback/
    Exchanges code for tokens, saves credentials to DoctorProfile, and redirects to dashboard.
    """
    def get(self, request, *args, **kwargs):
        state = request.session.get('google_oauth_state')
        code = request.GET.get('code')
        error = request.GET.get('error')

        if error:
            messages.error(request, f'Google Calendar connection authorization was denied: {error}')
            return redirect('appointment:doctor-dashboard')

        if not code:
            messages.error(request, 'No authorization code received from Google.')
            return redirect('appointment:doctor-dashboard')

        try:
            flow = get_google_oauth_flow(
                redirect_uri=getattr(settings, 'GOOGLE_REDIRECT_URI', 'https://docmed-fx0m.onrender.com/api/google/calendar/callback/')
            )
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Fetch user email using Google userInfo API or ID token
            calendar_email = None
            try:
                from googleapiclient.discovery import build
                user_info_service = build('oauth2', 'v2', credentials=credentials)
                user_info = user_info_service.userinfo().get().execute()
                calendar_email = user_info.get('email')
            except Exception as e:
                logger.warning(f'Could not fetch Google user email: {e}')

            if not request.user.is_authenticated:
                messages.error(request, 'Session expired during OAuth. Please log in as a Doctor.')
                return redirect('accounts:login')

            try:
                doctor_profile = request.user.doctor_profile
            except Exception:
                messages.error(request, 'Only registered Doctor profiles can connect Google Calendar.')
                return redirect('appointment:home')

            creds_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
            }

            doctor_profile.google_calendar_credentials = json.dumps(creds_data)
            doctor_profile.google_calendar_connected = True
            if calendar_email:
                doctor_profile.google_calendar_email = calendar_email

            doctor_profile.save(update_fields=[
                'google_calendar_credentials', 'google_calendar_connected', 'google_calendar_email'
            ])

            messages.success(
                request,
                f'🎉 Google Calendar successfully connected! ({calendar_email or "Primary Calendar"})'
            )
            return redirect('appointment:doctor-dashboard')

        except Exception as exc:
            logger.error(f'Error processing Google OAuth callback: {exc}', exc_info=True)
            messages.error(request, f'Failed to exchange Google OAuth code: {exc}')
            return redirect('appointment:doctor-dashboard')


class GoogleCalendarDisconnectView(LoginRequiredMixin, View):
    """
    Doctor Action: Disconnect Google Calendar.
    Clears credentials from DoctorProfile.
    """
    login_url = reverse_lazy('accounts:login')

    @method_decorator(doctor_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            doctor_profile = request.user.doctor_profile
            doctor_profile.google_calendar_credentials = None
            doctor_profile.google_calendar_connected = False
            doctor_profile.google_calendar_email = None
            doctor_profile.save(update_fields=[
                'google_calendar_credentials', 'google_calendar_connected', 'google_calendar_email'
            ])
            messages.info(request, 'Google Calendar has been disconnected from your account.')
        except Exception as exc:
            messages.error(request, f'Failed to disconnect Google Calendar: {exc}')

        return redirect('appointment:doctor-dashboard')


class GoogleCalendarSyncRetryView(LoginRequiredMixin, View):
    """
    Admin or Doctor Action: Retry Google Calendar & Meet Sync for a failed appointment.
    """
    login_url = reverse_lazy('accounts:login')

    def post(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id)

        # Access check: Doctor owner, Patient owner, or Staff
        is_doctor = (hasattr(request.user, 'doctor_profile') and booking.appointment.user == request.user)
        is_patient = (booking.user == request.user)
        is_admin = (request.user.is_staff or request.user.is_superuser)

        if not (is_doctor or is_patient or is_admin):
            messages.error(request, 'Permission denied.')
            return redirect('appointment:home')

        success = create_google_calendar_event(booking)

        if success:
            messages.success(
                request,
                f'🎉 Google Calendar Event & Meet Link successfully generated for Booking #{booking.id}!'
            )
        else:
            messages.error(
                request,
                f'Google Calendar Sync failed for Booking #{booking.id}. Ensure the Doctor has connected Google Calendar.'
            )

        if is_admin:
            return redirect('appointment:admin-dashboard')
        elif is_doctor:
            return redirect('appointment:doctor-dashboard')
        else:
            return redirect('appointment:patient-bookings')
