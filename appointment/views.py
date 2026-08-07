"""
Appointment views module.

Handles all appointment-related views including homepage listing,
doctor appointment CRUD, patient appointment requests, and search.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from django.db.models import Count, Sum, Avg, Q, F, DecimalField
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
import csv
import json
from django.http import HttpResponse

from accounts.forms import DoctorProfileUpdateForm, PatientProfileUpdateForm, DoctorProfileForm, PatientProfileForm
from accounts.models import User
from .decorators import user_is_doctor, user_is_patient
from .forms import CreateAppointmentForm, TakeAppointmentForm
from .models import Appointment, DEPARTMENT_CHOICES, DoctorProfile, Review, TakeAppointment


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

LOGIN_URL = reverse_lazy('accounts:login')


# ============================================================================
# Patient views
# ============================================================================


class EditPatientProfileView(LoginRequiredMixin, UpdateView):
    """Allow a patient to update their own user and profile details."""

    model = User
    form_class = PatientProfileUpdateForm
    context_object_name = 'patient'
    template_name = 'accounts/patient/edit-profile.html'
    success_url = reverse_lazy('accounts:patient-profile-update')
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['profile_form'] = PatientProfileForm(
                self.request.POST,
                self.request.FILES,
                instance=self.request.user.patient_profile
            )
        else:
            context['profile_form'] = PatientProfileForm(
                instance=self.request.user.patient_profile
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        if profile_form.is_valid():
            form.save()
            profile_form.save()
            from django.contrib import messages
            messages.success(self.request, "Your profile was successfully updated!")
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class TakeAppointmentView(LoginRequiredMixin, CreateView):
    """Allow a patient to book an appointment with a doctor."""

    template_name = 'appointment/take_appointment.html'
    form_class = TakeAppointmentForm
    extra_context = {'title': 'Take Appointment'}
    success_url = reverse_lazy('appointment:home')
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        # Send confirmation email notification to the patient
        from .emails import send_appointment_booked_email
        send_appointment_booked_email(form.instance)
        return response




# ============================================================================
# Doctor views
# ============================================================================


class EditDoctorProfileView(LoginRequiredMixin, UpdateView):
    """Allow a doctor to update their own user and profile details."""

    model = User
    form_class = DoctorProfileUpdateForm
    context_object_name = 'doctor'
    template_name = 'accounts/doctor/edit-profile.html'
    success_url = reverse_lazy('accounts:doctor-profile-update')
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['profile_form'] = DoctorProfileForm(
                self.request.POST,
                self.request.FILES,
                instance=self.request.user.doctor_profile
            )
        else:
            context['profile_form'] = DoctorProfileForm(
                instance=self.request.user.doctor_profile
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        if profile_form.is_valid():
            form.save()
            profile_form.save()
            from django.contrib import messages
            messages.success(self.request, "Your profile was successfully updated!")
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))



class AppointmentCreateView(LoginRequiredMixin, CreateView):
    """Allow a doctor to post a new appointment slot."""

    template_name = 'appointment/appointment_create.html'
    form_class = CreateAppointmentForm
    extra_context = {'title': 'Post New Appointment'}
    success_url = reverse_lazy('appointment:doctor-appointment')
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AppointmentListView(LoginRequiredMixin, ListView):
    """Show a doctor all their posted appointment slots."""

    model = Appointment
    template_name = 'appointment/appointment.html'
    context_object_name = 'appointment'
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects
            .filter(user=self.request.user)
            .order_by('-id')
        )


class PatientListView(LoginRequiredMixin, ListView):
    """Show a doctor all appointment requests from patients."""

    model = TakeAppointment
    context_object_name = 'patients'
    template_name = 'appointment/patient_list.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects
            .filter(appointment__user=self.request.user)
            .select_related('appointment', 'user')
            .order_by('-id')
        )


class PatientDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a patient's appointment request."""

    model = TakeAppointment
    success_url = reverse_lazy('appointment:patient-list')
    login_url = LOGIN_URL


class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an appointment slot created by a doctor."""

    model = Appointment
    success_url = reverse_lazy('appointment:doctor-appointment')
    login_url = LOGIN_URL


# ============================================================================
# Public views
# ============================================================================


class HomePageView(ListView):
    """Landing page showing all available appointment slots."""

    paginate_by = 6
    model = Appointment
    context_object_name = 'home'
    template_name = 'home.html'

    def get_queryset(self):
        return (
            self.model.objects
            .select_related('user')
            .order_by('-id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ── Live statistics ──────────────────────────────────────────────────
        total_doctors = User.objects.filter(role='doctor').count()
        total_patients = User.objects.filter(role='patient').count()
        total_appointments_slots = Appointment.objects.count()
        total_bookings = TakeAppointment.objects.count()

        # Count distinct hospitals from Doctor Profiles
        from django.db.models import Count, Avg, Sum
        total_hospitals = (
            DoctorProfile.objects
            .values('hospital')
            .exclude(hospital='')
            .distinct()
            .count()
        )

        # Satisfaction percentage dynamically calculated from ratings
        avg_rating = DoctorProfile.objects.aggregate(Avg('rating'))['rating__avg'] or 4.5
        satisfaction = min(99, int((avg_rating / 5.0) * 100))

        context['stats'] = {
            'total_doctors': total_doctors,
            'total_patients': total_patients,
            'total_hospitals': total_hospitals,
            'total_bookings': total_bookings,
            'satisfaction': satisfaction,
        }

        # ── Real-time available doctor (Hero Card) ──────────
        # Highest rated available doctor
        all_docs = list(DoctorProfile.objects.filter(is_verified=True).select_related('user'))
        available_docs = [doc for doc in all_docs if doc.is_available_now]
        # Using reverse=True instead of unary minus to safely sort multiple attributes
        available_docs.sort(key=lambda x: (x.rating, x.review_count), reverse=True)
        
        context['hero_doctor'] = available_docs[0] if available_docs else None

        # ── Featured doctors (6 Cards) ────────────────────────
        # 1. verified, available now, highest rated
        featured = available_docs[:6]
        
        # 2. if less than 6, fill with unavailable but verified, highest rated
        if len(featured) < 6:
            unavailable = [doc for doc in all_docs if not doc.is_available_now]
            unavailable.sort(key=lambda x: (x.rating, x.review_count), reverse=True)
            featured.extend(unavailable[:6 - len(featured)])
            
        # 3. if still less than 6, fill with unverified
        if len(featured) < 6:
            unverified = list(DoctorProfile.objects.filter(is_verified=False).select_related('user'))
            # Fix TypeError: bad operand type for unary -: 'datetime.datetime'
            unverified.sort(key=lambda x: (x.rating, x.created_at), reverse=True)
            featured.extend(unverified[:6 - len(featured)])
            
        context['featured_doctors'] = featured

        # ── Patient Reviews (Testimonials Slider) ─────────────
        context['reviews'] = (
            Review.objects
            .filter(is_approved=True)
            .select_related(
                'booking__user__patient_profile',
                'booking__appointment',
            )
            .order_by('-created_at', '-rating')
        )

        return context


class ServiceView(TemplateView):
    """Static services information page."""

    template_name = 'appointment/service.html'


class AboutView(TemplateView):
    """Static about information page."""

    template_name = 'about.html'


class ContactView(TemplateView):
    """Static contact information page."""

    template_name = 'contact.html'


class SearchView(ListView):
    """Search appointment slots by location and department with smart location fallback."""

    paginate_by = 6
    model = Appointment
    template_name = 'appointment/search.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        location     = self.request.GET.get('location', '').strip()
        department   = self.request.GET.get('department', '').strip()
        doctor_name  = self.request.GET.get('doctor_name', '').strip()
        experience   = self.request.GET.get('experience', '').strip()
        gender       = self.request.GET.get('gender', '').strip()
        max_distance = self.request.GET.get('max_distance', '0').strip()
        sort         = self.request.GET.get('sort', '').strip()
        user_lat     = self.request.GET.get('user_lat', '').strip()
        user_lng     = self.request.GET.get('user_lng', '').strip()

        # Parse GPS coords if provided
        try:
            self._user_lat = float(user_lat)
            self._user_lng = float(user_lng)
        except (ValueError, TypeError):
            self._user_lat = None
            self._user_lng = None

        try:
            self._max_distance = float(max_distance)
        except (ValueError, TypeError):
            self._max_distance = 0

        from django.db.models import Q

        # Base queryset — always prefetch related for performance
        qs = (
            self.model.objects
            .select_related('user', 'user__doctor_profile')
            .order_by('-created_at')
        )

        # Apply non-location filters first
        if department:
            qs = qs.filter(department__icontains=department)

        if doctor_name:
            qs = qs.filter(
                Q(full_name__icontains=doctor_name) |
                Q(user__first_name__icontains=doctor_name) |
                Q(user__last_name__icontains=doctor_name)
            )

        if gender:
            qs = qs.filter(user__gender=gender)

        if experience:
            if experience == '1-5':
                qs = qs.filter(user__doctor_profile__experience_years__gte=1,
                               user__doctor_profile__experience_years__lte=5)
            elif experience == '5-10':
                qs = qs.filter(user__doctor_profile__experience_years__gte=5,
                               user__doctor_profile__experience_years__lte=10)
            elif experience == '10+':
                qs = qs.filter(user__doctor_profile__experience_years__gte=10)

        # --- Location-based search with cascading fallback ---
        if location:
            # Level 0: Substring match on Appointment.location field
            loc_qs = qs.filter(location__icontains=location)
            if loc_qs.exists():
                self._fallback_level = None
                return loc_qs

            # Level 1: Same City in DoctorProfile
            same_city_qs = qs.filter(user__doctor_profile__city__iexact=location)
            if same_city_qs.exists():
                self._fallback_level = None
                return same_city_qs

            # Level 2: Nearby City (Haversine, 100 km radius)
            ref_lat, ref_lng = None, None
            ref_doc = DoctorProfile.objects.filter(city__iexact=location).first()
            if ref_doc and ref_doc.latitude and ref_doc.longitude:
                ref_lat, ref_lng = ref_doc.latitude, ref_doc.longitude
            elif self.request.user.is_authenticated:
                pat = getattr(self.request.user, 'patient_profile', None)
                if pat and pat.latitude and pat.longitude:
                    ref_lat, ref_lng = pat.latitude, pat.longitude

            if ref_lat is not None:
                import math
                nearby_ids = []
                for doc in DoctorProfile.objects.filter(
                        latitude__isnull=False, longitude__isnull=False):
                    rad = math.pi / 180
                    dlat = (doc.latitude - ref_lat) * rad
                    dlon = (doc.longitude - ref_lng) * rad
                    a = (math.sin(dlat / 2) ** 2 +
                         math.cos(ref_lat * rad) * math.cos(doc.latitude * rad) *
                         math.sin(dlon / 2) ** 2)
                    dist = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    if dist <= 100:  # km
                        nearby_ids.append(doc.user_id)
                if nearby_ids:
                    nearby_qs = qs.filter(user_id__in=nearby_ids)
                    if nearby_qs.exists():
                        self._fallback_level = 'nearby'
                        return nearby_qs

            # Level 3: Same State
            state_qs = qs.filter(user__doctor_profile__state__iexact=location)
            if state_qs.exists():
                self._fallback_level = 'state'
                return state_qs

            # Level 4: Any Available Doctor
            avail_ids = [
                doc.user_id for doc in DoctorProfile.objects.all()
                if doc.is_available_now
            ]
            avail_qs = qs.filter(user_id__in=avail_ids)
            if avail_qs.exists():
                self._fallback_level = 'any'
                return avail_qs

            # Level 5: Return everything (never empty if DB has data)
            self._fallback_level = 'any'
            return qs

        # --- GPS distance filtering ---
        if self._user_lat is not None and self._user_lng is not None:
            import math
            ref_lat, ref_lng = self._user_lat, self._user_lng
            filtered_ids = []
            self._distance_map = {}
            for apt in qs.select_related('user__doctor_profile'):
                dp = getattr(apt.user, 'doctor_profile', None)
                if dp and dp.latitude and dp.longitude:
                    rad = math.pi / 180
                    dlat = (dp.latitude - ref_lat) * rad
                    dlon = (dp.longitude - ref_lng) * rad
                    a = (math.sin(dlat / 2) ** 2 +
                         math.cos(ref_lat * rad) * math.cos(dp.latitude * rad) *
                         math.sin(dlon / 2) ** 2)
                    dist = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    if self._max_distance <= 0 or dist <= self._max_distance:
                        filtered_ids.append(apt.id)
                        self._distance_map[apt.id] = round(dist, 1)
            if filtered_ids:
                qs = qs.filter(id__in=filtered_ids)
        else:
            self._distance_map = {}

        # --- Sorting ---
        sort = self.request.GET.get('sort', '').strip()
        if sort == 'rating':
            qs = qs.order_by('-user__doctor_profile__rating')
        elif sort == 'experience':
            qs = qs.order_by('-user__doctor_profile__experience_years')
        elif sort == 'fee_low':
            qs = qs.order_by('appointment_fee')
        elif sort == 'distance' and self._distance_map:
            # Sort by computed distance
            id_order = sorted(self._distance_map.keys(), key=lambda k: self._distance_map[k])
            preserved = {apt_id: idx for idx, apt_id in enumerate(id_order)}
            qs = sorted(qs, key=lambda apt: preserved.get(apt.id, 9999))
            return qs

        self._fallback_level = None
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass department choices so template can build the dropdown dynamically
        context['dept_choices'] = DEPARTMENT_CHOICES
        # Pass fallback level so template can show an informative message
        context['fallback_level'] = getattr(self, '_fallback_level', None)
        # Pass Google Maps API key (placeholder — set GOOGLE_MAPS_API_KEY in settings or env)
        from django.conf import settings as django_settings
        context['google_maps_api_key'] = getattr(django_settings, 'GOOGLE_MAPS_API_KEY', '')
        # Annotate distance_km onto each result
        distance_map = getattr(self, '_distance_map', {})
        for apt in context.get(self.context_object_name, []):
            apt.distance_km = distance_map.get(apt.id)
        return context


# ============================================================================
# Doctor booking management actions
# ============================================================================

from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.dateparse import parse_datetime

class ApproveBookingView(LoginRequiredMixin, View):
    """Allow doctors to approve a patient's booking request."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, appointment__user=request.user)
        booking.status = 'approved'

        # Generate Google Meet link & create Google Calendar event
        try:
            from .google_calendar_service import create_google_meeting
            meet_url = create_google_meeting(booking)
            if meet_url:
                booking.meeting_url = meet_url
                booking.meeting_provider = 'meet'
        except Exception as exc:
            logger.warning(f"Google Calendar/Meet event creation skipped: {exc}")

        booking.save()

        # Send confirmation email
        from .emails import send_appointment_status_update_email
        send_appointment_status_update_email(booking, 'Approved')

        # Send FCM Push Notification to Patient
        try:
            from .fcm_service import notify_appointment_approved
            notify_appointment_approved(booking)
        except Exception as exc:
            logger.warning(f"FCM push notification skipped: {exc}")

        messages.success(request, f"Appointment booking for {booking.full_name} has been approved.")
        return redirect('appointment:patient-list')


class CancelBookingView(LoginRequiredMixin, View):
    """Allow doctors to cancel a patient's booking request."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, appointment__user=request.user)
        booking.status = 'cancelled'
        booking.save()

        # Cancel Google Calendar event if exists
        if getattr(booking, 'google_calendar_event_id', None):
            try:
                from .google_calendar_service import cancel_calendar_event_async
                cancel_calendar_event_async(booking.google_calendar_event_id)
            except Exception as exc:
                logger.warning(f"Google Calendar event cancellation skipped: {exc}")

        # Send confirmation email
        from .emails import send_appointment_status_update_email
        send_appointment_status_update_email(booking, 'Cancelled')

        # Send FCM Push Notification to Patient
        try:
            from .fcm_service import notify_appointment_cancelled
            notify_appointment_cancelled(booking)
        except Exception as exc:
            logger.warning(f"FCM push notification skipped: {exc}")

        messages.warning(request, f"Appointment booking for {booking.full_name} has been cancelled.")
        return redirect('appointment:patient-list')


class RescheduleBookingView(LoginRequiredMixin, View):
    """Allow doctors to reschedule a patient's booking date and time."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, appointment__user=request.user)
        new_date_str = request.POST.get('new_date')

        if new_date_str:
            try:
                booking.date = parse_datetime(new_date_str)
                booking.status = 'rescheduled'
                booking.save()

                # Send confirmation email
                from .emails import send_appointment_status_update_email
                send_appointment_status_update_email(booking, 'Rescheduled')

                # Send FCM Push Notification to Patient
                try:
                    from .fcm_service import notify_appointment_rescheduled
                    notify_appointment_rescheduled(booking)
                except Exception as exc:
                    logger.warning(f"FCM push notification skipped: {exc}")

                messages.success(request, f"Appointment booking for {booking.full_name} has been rescheduled.")
            except Exception:
                messages.error(request, "Failed to reschedule. Invalid date/time format.")
        else:
            messages.error(request, "Please specify a valid date and time to reschedule.")

        return redirect('appointment:patient-list')


# ============================================================================
# Patient bookings dashboard
# ============================================================================

# ============================================================================
# Patient bookings dashboard
# ============================================================================

class PatientBookingsListView(LoginRequiredMixin, ListView):
    """Display a list of bookings created by the currently logged-in patient."""
    model = TakeAppointment
    context_object_name = 'bookings'
    template_name = 'appointment/patient_bookings.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects
            .filter(user=self.request.user)
            .select_related('appointment', 'appointment__user', 'appointment__user__doctor_profile')
            .order_by('-date')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_bookings = list(self.get_queryset())
        
        # Segment bookings into upcoming and past
        now = timezone.now()
        upcoming = []
        past = []
        for b in all_bookings:
            if b.status in ['pending', 'approved', 'rescheduled'] and b.date >= now:
                upcoming.append(b)
            else:
                past.append(b)
                
        context['upcoming_bookings'] = upcoming
        context['past_bookings'] = past
        
        # Dashboard stats
        context['stats'] = {
            'total': len(all_bookings),
            'pending': sum(1 for b in all_bookings if b.status == 'pending'),
            'approved': sum(1 for b in all_bookings if b.status == 'approved'),
            'cancelled': sum(1 for b in all_bookings if b.status == 'cancelled'),
            'completed': sum(1 for b in all_bookings if b.status == 'completed'),
        }
        return context


class PatientCancelBookingView(LoginRequiredMixin, View):
    """Allow patients to cancel their own bookings."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, user=request.user)
        if booking.status in ['pending', 'approved', 'rescheduled']:
            booking.status = 'cancelled'
            booking.save()
            from .emails import send_appointment_status_update_email
            send_appointment_status_update_email(booking, 'Cancelled')
            messages.success(request, "Your appointment has been successfully cancelled.")
        else:
            messages.error(request, "This appointment status cannot be cancelled.")
        return redirect('appointment:patient-bookings')


class PatientRescheduleBookingView(LoginRequiredMixin, View):
    """Allow patients to reschedule their own bookings."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, user=request.user)
        new_date_str = request.POST.get('new_date')
        if new_date_str:
            try:
                booking.date = parse_datetime(new_date_str)
                booking.status = 'rescheduled'
                booking.save()
                from .emails import send_appointment_status_update_email
                send_appointment_status_update_email(booking, 'Rescheduled')
                messages.success(request, "Your appointment was successfully rescheduled.")
            except Exception:
                messages.error(request, "Failed to reschedule. Invalid date/time format.")
        else:
            messages.error(request, "Please specify a valid date and time to reschedule.")
        return redirect('appointment:patient-bookings')


# ============================================================================
# Doctor dashboard and status actions
# ============================================================================

class DoctorDashboardView(LoginRequiredMixin, TemplateView):
    """Unified Doctor Dashboard displaying stats, operational slots, and bookings."""
    template_name = 'appointment/doctor_dashboard.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Operational slots posted by this doctor
        slots = Appointment.objects.filter(user=user).order_by('-created_at')
        
        # Bookings for this doctor's slots
        bookings = TakeAppointment.objects.filter(
            appointment__user=user
        ).select_related('appointment', 'user', 'user__patient_profile').order_by('-date')
        
        # Stats calculations
        total_slots = slots.count()
        total_bookings = bookings.count()
        pending_bookings = bookings.filter(status='pending').count()
        approved_bookings = bookings.filter(status='approved').count()
        completed_bookings = bookings.filter(status='completed').count()
        
        # Total patients treated
        unique_patients = bookings.filter(status='completed').values('user').distinct().count()
        
        # Earnings calculation based on completed appointments
        profile = getattr(user, 'doctor_profile', None)
        fee = profile.consultation_fee if profile else 0
        total_earnings = completed_bookings * fee
        
        # Segment bookings
        now = timezone.now()
        pending_list = []
        upcoming_list = []
        past_list = []
        
        for b in bookings:
            if b.status == 'pending':
                pending_list.append(b)
            elif b.status in ['approved', 'rescheduled'] and b.date >= now:
                upcoming_list.append(b)
            else:
                past_list.append(b)

        context['slots'] = slots
        context['pending_bookings'] = pending_list
        context['upcoming_bookings'] = upcoming_list
        context['past_bookings'] = past_list
        
        context['stats'] = {
            'total_slots': total_slots,
            'total_bookings': total_bookings,
            'pending': pending_bookings,
            'approved': approved_bookings,
            'completed': completed_bookings,
            'patients': unique_patients,
            'earnings': total_earnings,
            'fee': fee,
            'is_online': profile.is_online if profile else False
        }
        return context


class CompleteBookingView(LoginRequiredMixin, View):
    """Mark appointment booking as completed with optional notes."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, appointment__user=request.user)
        notes = request.POST.get('doctor_notes', '').strip()
        booking.status = 'completed'
        booking.doctor_notes = notes
        booking.save()
        
        # Increment patients treated in doctor profile
        profile = getattr(request.user, 'doctor_profile', None)
        if profile:
            profile.patients_treated += 1
            profile.save()

        # Send confirmation email
        from .emails import send_appointment_status_update_email
        send_appointment_status_update_email(booking, 'Completed')

        messages.success(request, f"Appointment booking for {booking.full_name} is marked as Completed.")
        return redirect('appointment:doctor-appointment')


class RejectBookingView(LoginRequiredMixin, View):
    """Mark appointment booking as rejected."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, appointment__user=request.user)
        booking.status = 'rejected'
        booking.save()

        # Send confirmation email
        from .emails import send_appointment_status_update_email
        send_appointment_status_update_email(booking, 'Rejected')

        messages.warning(request, f"Appointment booking for {booking.full_name} has been rejected.")
        return redirect('appointment:doctor-appointment')


class MarkMissedBookingView(LoginRequiredMixin, View):
    """Mark appointment booking as missed."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk, appointment__user=request.user)
        booking.status = 'missed'
        booking.save()

        messages.info(request, f"Appointment booking for {booking.full_name} has been marked as Missed.")
        return redirect('appointment:doctor-appointment')


class ToggleAvailabilityView(LoginRequiredMixin, View):
    """Toggle online availability status for doctors."""
    login_url = LOGIN_URL

    def post(self, request, *args, **kwargs):
        profile = getattr(request.user, 'doctor_profile', None)
        if profile:
            profile.is_online = not profile.is_online
            profile.save()
            status_str = "Online" if profile.is_online else "Offline"
            messages.success(request, f"Your availability status has been updated to {status_str}.")
        return redirect('appointment:doctor-appointment')


# ============================================================================
# Admin Custom Dashboard & Review Verification Actions
# ============================================================================

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Admin Dashboard for managing doctors, reviews, and massive stats."""
    template_name = 'appointment/admin_dashboard.html'
    login_url = LOGIN_URL

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            messages.error(request, "Access denied. Admin credentials required.")
            return redirect('appointment:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- Time Filtering ---
        now = timezone.now()
        date_range = self.request.GET.get('range', '30d')
        start_date = None
        
        if date_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'yesterday':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif date_range == '7d':
            start_date = now - timedelta(days=7)
        elif date_range == '30d':
            start_date = now - timedelta(days=30)
        elif date_range == '3m':
            start_date = now - timedelta(days=90)
        elif date_range == '1y':
            start_date = now - timedelta(days=365)
            
        # --- Base Querysets ---
        users_qs = User.objects.all()
        doctors_qs = DoctorProfile.objects.select_related('user')
        bookings_qs = TakeAppointment.objects.all()
        
        # Prevent circular import or missing import error for Payment
        from appointment.models import Payment, DEPARTMENT_CHOICES
        payments_qs = Payment.objects.all()
        
        # Current range querysets
        b_qs = bookings_qs.filter(date__gte=start_date) if start_date else bookings_qs
        p_qs = payments_qs.filter(created_at__gte=start_date) if start_date else payments_qs
        
        # --- Dashboard Overview Stats ---
        total_patients = users_qs.filter(role='patient').count()
        total_doctors = doctors_qs.count()
        total_appointments = bookings_qs.count()
        
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        todays_appointments = bookings_qs.filter(date__gte=today_start, date__lt=today_start + timedelta(days=1)).count()
        upcoming_appointments = bookings_qs.filter(date__gt=now).count()
        completed_appointments = bookings_qs.filter(status='completed').count()
        cancelled_appointments = bookings_qs.filter(status='cancelled').count()
        pending_appointments = bookings_qs.filter(status='pending').count()
        
        active_doctors = doctors_qs.filter(is_verified=True).count()
        online_doctors = doctors_qs.filter(is_verified=True, is_online=True).count()
        hospitals_registered = doctors_qs.exclude(hospital='').values('hospital').distinct().count()
        
        total_revenue = payments_qs.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0)
        monthly_revenue = payments_qs.filter(status='success', created_at__gte=this_month_start).aggregate(Sum('amount'))['amount__sum'] or 0
        this_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        yearly_revenue = payments_qs.filter(status='success', created_at__gte=this_year_start).aggregate(Sum('amount'))['amount__sum'] or 0
        
        reviews_qs = Review.objects.all()
        avg_rating = reviews_qs.aggregate(Avg('rating'))['rating__avg'] or 5.0
        total_reviews = reviews_qs.count()
        total_departments = len(DEPARTMENT_CHOICES)
        
        # Assign Overview Stats
        context['stats'] = {
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'total_appointments': total_appointments,
            'todays_appointments': todays_appointments,
            'upcoming_appointments': upcoming_appointments,
            'completed_appointments': completed_appointments,
            'cancelled_appointments': cancelled_appointments,
            'pending_appointments': pending_appointments,
            'active_doctors': active_doctors,
            'online_doctors': online_doctors,
            'hospitals_registered': hospitals_registered,
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
            'avg_rating': round(avg_rating, 1),
            'total_reviews': total_reviews,
            'total_departments': total_departments,
            'unverified_doctors': doctors_qs.filter(is_verified=False).count(),
            'pending_reviews': reviews_qs.filter(is_approved=False).count(),
        }

        # --- Chart Data ---
        # 1. Daily Appointment Line Chart
        daily_bookings = list(b_qs.annotate(day=TruncDate('date')).values('day').annotate(count=Count('id')).order_by('day'))
        context['chart_daily_appointments_labels'] = [d['day'].strftime('%b %d') for d in daily_bookings if d['day']]
        context['chart_daily_appointments_data'] = [d['count'] for d in daily_bookings if d['day']]
        
        # 2. Monthly Appointment Bar Chart
        monthly_bookings = list(bookings_qs.annotate(month=TruncMonth('date')).values('month').annotate(count=Count('id')).order_by('month'))
        context['chart_monthly_appointments_labels'] = [d['month'].strftime('%b %Y') for d in monthly_bookings if d['month']]
        context['chart_monthly_appointments_data'] = [d['count'] for d in monthly_bookings if d['month']]
        
        # 3. Revenue Trend Line Chart
        daily_revenue = list(p_qs.filter(status='success').annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('amount')).order_by('day'))
        context['chart_revenue_trend_labels'] = [d['day'].strftime('%b %d') for d in daily_revenue if d['day']]
        context['chart_revenue_trend_data'] = [float(d['total']) for d in daily_revenue if d['day']]
        
        # 4. Revenue by Month Bar Chart
        monthly_rev_data = list(payments_qs.filter(status='success').annotate(month=TruncMonth('created_at')).values('month').annotate(total=Sum('amount')).order_by('month'))
        context['chart_revenue_month_labels'] = [d['month'].strftime('%b %Y') for d in monthly_rev_data if d['month']]
        context['chart_revenue_month_data'] = [float(d['total']) for d in monthly_rev_data if d['month']]
        
        # 5. Most Popular Department Pie Chart
        dept_data = list(b_qs.values('appointment__department').annotate(count=Count('id')).order_by('-count'))
        context['chart_pop_dept_labels'] = [d['appointment__department'] for d in dept_data]
        context['chart_pop_dept_data'] = [d['count'] for d in dept_data]
        
        # 6. Doctor Specialization Pie Chart
        spec_data = list(doctors_qs.values('specialization').annotate(count=Count('id')).order_by('-count'))
        context['chart_doc_spec_labels'] = [d['specialization'] for d in spec_data if d['specialization']]
        context['chart_doc_spec_data'] = [d['count'] for d in spec_data if d['specialization']]
        
        # 7. Appointment Status Doughnut Chart
        status_data = list(b_qs.values('status').annotate(count=Count('id')).order_by('-count'))
        context['chart_status_labels'] = [d['status'].title() for d in status_data]
        context['chart_status_data'] = [d['count'] for d in status_data]
        
        # 8. Top Doctors Horizontal Bar Chart (By Revenue)
        top_docs_rev = list(
            payments_qs.filter(status='success')
            .values(doc_name=F('booking__appointment__full_name'))
            .annotate(total=Sum('amount'))
            .order_by('-total')[:10]
        )
        context['chart_top_docs_labels'] = [d['doc_name'] for d in top_docs_rev]
        context['chart_top_docs_data'] = [float(d['total']) for d in top_docs_rev]

        # 9. Patients Registration Trend
        daily_patients = list(users_qs.filter(role='patient').annotate(day=TruncDate('date_joined')).values('day').annotate(count=Count('id')).order_by('day'))
        context['chart_patient_reg_labels'] = [d['day'].strftime('%b %d') for d in daily_patients if d['day']]
        context['chart_patient_reg_data'] = [d['count'] for d in daily_patients if d['day']]
        
        # 10. Doctor Registration Trend
        daily_doctors = list(users_qs.filter(role='doctor').annotate(day=TruncDate('date_joined')).values('day').annotate(count=Count('id')).order_by('day'))
        context['chart_doctor_reg_labels'] = [d['day'].strftime('%b %d') for d in daily_doctors if d['day']]
        context['chart_doctor_reg_data'] = [d['count'] for d in daily_doctors if d['day']]

        # --- Top Doctors Section ---
        top_doctors_query = DoctorProfile.objects.select_related('user').annotate(
            total_rev=Sum('user__appointments__bookings__payment__amount', filter=Q(user__appointments__bookings__payment__status='success')),
            completed_appts=Count('user__appointments__bookings', filter=Q(user__appointments__bookings__status='completed'))
        ).order_by('-rating', '-total_rev')[:15]
        context['top_doctors'] = top_doctors_query

        # --- Most Popular Departments ---
        dep_stats = []
        for dept, dept_label in DEPARTMENT_CHOICES:
            dept_appts = Appointment.objects.filter(department=dept)
            doc_cnt = dept_appts.values('user').distinct().count()
            bk_cnt = TakeAppointment.objects.filter(appointment__department=dept).count()
            comp_cnt = TakeAppointment.objects.filter(appointment__department=dept, status='completed').count()
            rev = Payment.objects.filter(booking__appointment__department=dept, status='success').aggregate(Sum('amount'))['amount__sum'] or 0
            rate = (comp_cnt / bk_cnt * 100) if bk_cnt > 0 else 0
            
            avg_r = Review.objects.filter(booking__appointment__department=dept).aggregate(Avg('rating'))['rating__avg'] or 5.0
            
            if doc_cnt > 0 or bk_cnt > 0:
                dep_stats.append({
                    'name': dept_label,
                    'doctor_count': doc_cnt,
                    'booking_count': bk_cnt,
                    'revenue': float(rev),
                    'completion_rate': round(rate, 1),
                    'avg_rating': round(avg_r, 1)
                })
        
        dep_stats.sort(key=lambda x: x['booking_count'], reverse=True)
        context['popular_departments'] = dep_stats

        # --- Recent Activities ---
        r_bookings = list(TakeAppointment.objects.select_related('user', 'appointment').order_by('-date')[:10])
        r_payments = list(Payment.objects.select_related('booking').order_by('-created_at')[:10])
        r_users = list(User.objects.order_by('-date_joined')[:10])
        
        activities = []
        for b in r_bookings:
            activities.append({'type': 'Booking', 'title': f'Booking {b.status.title()} by {b.full_name}', 'time': b.date, 'icon': 'calendar-check-o', 'color': 'primary'})
        for p in r_payments:
            activities.append({'type': 'Payment', 'title': f'Payment {p.status.title()} for {p.amount}', 'time': p.created_at, 'icon': 'credit-card', 'color': 'success'})
        for u in r_users:
            role = u.role.title() if u.role else 'User'
            activities.append({'type': 'Registration', 'title': f'New {role} Registered: {u.first_name}', 'time': u.date_joined, 'icon': 'user-plus', 'color': 'info'})
            
        activities.sort(key=lambda x: x['time'], reverse=True)
        context['recent_activities'] = activities[:15]
        
        # Appointment & Revenue Analytics specific
        context['appt_analytics'] = {
            'today': todays_appointments,
            'weekly': bookings_qs.filter(date__gte=now - timedelta(days=7)).count(),
            'monthly': bookings_qs.filter(date__gte=now - timedelta(days=30)).count(),
            'cancelled_pct': round((cancelled_appointments / total_appointments * 100) if total_appointments else 0, 1),
            'completed_pct': round((completed_appointments / total_appointments * 100) if total_appointments else 0, 1),
            'rescheduled_pct': round((bookings_qs.filter(status='rescheduled').count() / total_appointments * 100) if total_appointments else 0, 1),
            'avg_time': 30
        }
        
        refunds = payments_qs.filter(status='refunded').aggregate(Sum('amount'))['amount__sum'] or 0
        total_txn = payments_qs.filter(status='success').count()
        context['rev_analytics'] = {
            'today': payments_qs.filter(status='success', created_at__gte=today_start).aggregate(Sum('amount'))['amount__sum'] or 0,
            'weekly': payments_qs.filter(status='success', created_at__gte=now - timedelta(days=7)).aggregate(Sum('amount'))['amount__sum'] or 0,
            'monthly': monthly_revenue,
            'yearly': yearly_revenue,
            'pending': payments_qs.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
            'refunds': refunds,
            'avg_txn': round(total_revenue / total_txn, 2) if total_txn else 0,
            'top_dept': dep_stats[0]['name'] if dep_stats else 'N/A',
            'top_doc': top_docs_rev[0]['doc_name'] if top_docs_rev else 'N/A'
        }
        
        context['unverified_doctor_profiles'] = doctors_qs.filter(is_verified=False).order_by('-created_at')
        context['pending_review_list'] = reviews_qs.filter(is_approved=False).order_by('-created_at')
        context['current_range'] = date_range

        # Serialize lists for chart js
        context['chart_daily_appointments_labels'] = json.dumps(context['chart_daily_appointments_labels'])
        context['chart_daily_appointments_data'] = json.dumps(context['chart_daily_appointments_data'])
        context['chart_monthly_appointments_labels'] = json.dumps(context['chart_monthly_appointments_labels'])
        context['chart_monthly_appointments_data'] = json.dumps(context['chart_monthly_appointments_data'])
        context['chart_revenue_trend_labels'] = json.dumps(context['chart_revenue_trend_labels'])
        context['chart_revenue_trend_data'] = json.dumps(context['chart_revenue_trend_data'])
        context['chart_revenue_month_labels'] = json.dumps(context['chart_revenue_month_labels'])
        context['chart_revenue_month_data'] = json.dumps(context['chart_revenue_month_data'])
        context['chart_pop_dept_labels'] = json.dumps(context['chart_pop_dept_labels'])
        context['chart_pop_dept_data'] = json.dumps(context['chart_pop_dept_data'])
        context['chart_doc_spec_labels'] = json.dumps(context['chart_doc_spec_labels'])
        context['chart_doc_spec_data'] = json.dumps(context['chart_doc_spec_data'])
        context['chart_status_labels'] = json.dumps(context['chart_status_labels'])
        context['chart_status_data'] = json.dumps(context['chart_status_data'])
        context['chart_top_docs_labels'] = json.dumps(context['chart_top_docs_labels'])
        context['chart_top_docs_data'] = json.dumps(context['chart_top_docs_data'])
        context['chart_patient_reg_labels'] = json.dumps(context['chart_patient_reg_labels'])
        context['chart_patient_reg_data'] = json.dumps(context['chart_patient_reg_data'])
        context['chart_doctor_reg_labels'] = json.dumps(context['chart_doctor_reg_labels'])
        context['chart_doctor_reg_data'] = json.dumps(context['chart_doctor_reg_data'])

        return context


class AdminDashboardStatsAPIView(LoginRequiredMixin, View):
    """AJAX API endpoint for real-time stats updates."""
    login_url = LOGIN_URL

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        from appointment.models import Payment, DEPARTMENT_CHOICES
        
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0)
        
        users_qs = User.objects.all()
        doctors_qs = DoctorProfile.objects.all()
        bookings_qs = TakeAppointment.objects.all()
        payments_qs = Payment.objects.all()
        reviews_qs = Review.objects.all()
        
        total_patients = users_qs.filter(role='patient').count()
        total_doctors = doctors_qs.count()
        active_doctors = doctors_qs.filter(is_verified=True).count()
        online_doctors = doctors_qs.filter(is_verified=True, is_online=True).count()
        
        total_appointments = bookings_qs.count()
        todays_appointments = bookings_qs.filter(date__gte=today_start, date__lt=today_start + timedelta(days=1)).count()
        upcoming_appointments = bookings_qs.filter(date__gt=now).count()
        completed_appointments = bookings_qs.filter(status='completed').count()
        cancelled_appointments = bookings_qs.filter(status='cancelled').count()
        pending_appointments = bookings_qs.filter(status='pending').count()
        
        total_revenue = payments_qs.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_revenue = payments_qs.filter(status='success', created_at__gte=this_month_start).aggregate(Sum('amount'))['amount__sum'] or 0
        
        avg_rating = reviews_qs.aggregate(Avg('rating'))['rating__avg'] or 5.0
        
        data = {
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'active_doctors': active_doctors,
            'online_doctors': online_doctors,
            'total_appointments': total_appointments,
            'todays_appointments': todays_appointments,
            'completed_appointments': completed_appointments,
            'cancelled_appointments': cancelled_appointments,
            'pending_appointments': pending_appointments,
            'upcoming_appointments': upcoming_appointments,
            'total_revenue': float(total_revenue),
            'monthly_revenue': float(monthly_revenue),
            'avg_rating': round(float(avg_rating), 1),
            'total_departments': len(DEPARTMENT_CHOICES),
        }
        return JsonResponse(data)


class AdminExportCSVView(LoginRequiredMixin, View):
    """Exports Dashboard Analytics Data to CSV."""
    login_url = LOGIN_URL

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            return redirect('appointment:home')
            
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="docmed_analytics_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Report Generation Date', timezone.now().strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])
        
        writer.writerow(['Top Doctors by Revenue'])
        writer.writerow(['Doctor Name', 'Department', 'Hospital', 'Completed Bookings', 'Total Revenue'])
        
        top_doctors = DoctorProfile.objects.annotate(
            total_rev=Sum('user__appointments__bookings__payment__amount', filter=Q(user__appointments__bookings__payment__status='success')),
            completed_appts=Count('user__appointments__bookings', filter=Q(user__appointments__bookings__status='completed'))
        ).order_by('-total_rev')
        
        for doc in top_doctors:
            writer.writerow([
                f"Dr. {doc.user.first_name} {doc.user.last_name}", 
                doc.specialization,
                doc.hospital,
                doc.completed_appts,
                doc.total_rev or 0
            ])
            
        writer.writerow([])
        writer.writerow(['Recent Bookings'])
        writer.writerow(['Patient', 'Doctor', 'Date', 'Status'])
        bookings = TakeAppointment.objects.select_related('user', 'appointment').order_by('-date')[:50]
        for b in bookings:
            writer.writerow([b.full_name, b.appointment.full_name, b.date.strftime('%Y-%m-%d'), b.status])

        return response


class VerifyDoctorView(LoginRequiredMixin, View):
    """Allow admins to verify doctor profile badges."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            return redirect('appointment:home')
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        doctor.is_verified = True
        doctor.save()
        messages.success(request, f"Dr. {doctor.user.first_name} {doctor.user.last_name} has been verified.")
        return redirect('appointment:admin-dashboard')


class ApproveReviewView(LoginRequiredMixin, View):
    """Allow admins to approve reviews for homepage visibility."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            return redirect('appointment:home')
        review = get_object_or_404(Review, pk=pk)
        review.is_approved = True
        review.save()

        # Recalculate doctor rating based on approved reviews
        doctor = getattr(review.booking.appointment.user, 'doctor_profile', None)
        if doctor:
            from django.db.models import Avg
            approved_reviews = Review.objects.filter(booking__appointment__user=doctor.user, is_approved=True)
            avg_r = approved_reviews.aggregate(Avg('rating'))['rating__avg']
            count = approved_reviews.count()
            doctor.rating = round(avg_r, 1) if avg_r else 5.0
            doctor.review_count = count
            doctor.save()

        messages.success(request, "Review has been approved and is now visible on the homepage.")
        return redirect('appointment:admin-dashboard')


class RejectReviewView(LoginRequiredMixin, View):
    """Allow admins to delete/reject reviews."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            return redirect('appointment:home')
        review = get_object_or_404(Review, pk=pk)
        review.delete()
        messages.info(request, "Review has been rejected and removed.")
        return redirect('appointment:admin-dashboard')


# ============================================================================
# Video Consultation (Multi-Provider: Jitsi, Google Meet, Zoom)
# ============================================================================

from .google_meet_service import create_google_meeting
from .zoom_service import create_zoom_meeting
from .jitsi_service import create_jitsi_meeting
from .models import MeetingChatMessage, MeetingFile
import os

class CreateMeetingView(LoginRequiredMixin, View):
    """
    Doctor creates a video consultation meeting room link.
    Supports Jitsi Meet, Google Meet, or Zoom.
    """
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)

        if booking.appointment.user != request.user:
            messages.error(request, "You can only create meetings for your own patients.")
            return redirect('appointment:doctor-appointment')

        provider = request.POST.get('provider', 'jitsi').lower()

        try:
            if provider == 'google':
                meeting_url = create_google_meeting(booking)
                provider_name = 'Google Meet'
            elif provider == 'zoom':
                meeting_url = create_zoom_meeting(booking)
                provider_name = 'Zoom'
            else:
                meeting_url = create_jitsi_meeting(booking)
                provider_name = 'Jitsi Meet'
                provider = 'jitsi'

            booking.meeting_url = meeting_url
            booking.meeting_provider = provider
            booking.meeting_status = 'waiting'  # Initial status is waiting room
            booking.save(update_fields=['meeting_url', 'meeting_provider', 'meeting_status'])

            messages.success(request, f"Telemedicine session ({provider_name}) created! Join code shared with patient.")
        except Exception as e:
            messages.error(request, f"Error generating meeting link: {str(e)}")

        return redirect('appointment:doctor-appointment')


class JoinMeetingView(LoginRequiredMixin, View):
    """
    Renders the Telemedicine session interface containing the call frame,
    waiting room overlay, meeting chat, notes section, and document sharing.
    """
    login_url = LOGIN_URL

    def get(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)

        is_patient = booking.user == request.user
        is_doctor = booking.appointment.user == request.user
        if not is_patient and not is_doctor:
            messages.error(request, "You don't have access to this meeting.")
            return redirect('appointment:home')

        if not booking.meeting_url:
            messages.warning(request, "No video consultation link has been created yet.")
            if is_patient:
                return redirect('appointment:patient-bookings')
            return redirect('appointment:doctor-appointment')

        context = {
            'booking': booking,
            'meeting_url': booking.meeting_url,
            'is_doctor': is_doctor,
            'is_patient': is_patient,
            'meeting_status': booking.meeting_status,
            'meeting_notes': booking.meeting_notes,
            'meeting_provider': booking.meeting_provider,
        }
        return render(request, 'appointment/video_consultation.html', context)


# ============================================================================
# Tele-Health AJAX APIs (Chat, File uploads, and Session Management)
# ============================================================================

from django.http import JsonResponse

class MeetingChatAPIView(LoginRequiredMixin, View):
    """
    AJAX endpoint to retrieve and post messages during a meeting consultation.
    """
    def get(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)
        
        if booking.user != request.user and booking.appointment.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        messages_qs = booking.chat_messages.select_related('sender').order_by('created_at')
        
        # Support incremental polling via ?after=<id>
        after_id = request.GET.get('after', 0)
        try:
            after_id = int(after_id)
        except (ValueError, TypeError):
            after_id = 0
        if after_id > 0:
            messages_qs = messages_qs.filter(id__gt=after_id)
        
        # Mark other sender's messages as read
        unread_ids = messages_qs.exclude(sender=request.user).filter(is_seen=False).values_list('id', flat=True)
        if unread_ids:
            booking.chat_messages.filter(id__in=list(unread_ids)).update(is_seen=True)
        
        messages_list = [{
            'id': msg.id,
            'sender_id': msg.sender.id,
            'is_self': msg.sender == request.user,
            'sender_name': f"Dr. {msg.sender.get_full_name()}" if msg.sender.role == 'doctor' else msg.sender.get_full_name(),
            'sender_role': msg.sender.role,
            'message': msg.message,
            'timestamp': msg.created_at.strftime('%I:%M %p'),
            'is_seen': msg.is_seen
        } for msg in messages_qs]
        
        return JsonResponse({'messages': messages_list})

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)
        
        if booking.user != request.user and booking.appointment.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        import json
        try:
            data = json.loads(request.body)
            message_text = data.get('message', '').strip()
        except Exception:
            message_text = request.POST.get('message', '').strip()

        if not message_text:
            return JsonResponse({'error': 'Message text is required'}, status=400)

        msg = MeetingChatMessage.objects.create(
            booking=booking,
            sender=request.user,
            message=message_text
        )
        
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': msg.id,
                'sender_name': f"Dr. {msg.sender.get_full_name()}" if msg.sender.role == 'doctor' else msg.sender.get_full_name(),
                'sender_role': msg.sender.role,
                'message': msg.message,
                'timestamp': msg.created_at.strftime('%I:%M %p')
            }
        })


class MeetingFileAPIView(LoginRequiredMixin, View):
    """
    AJAX endpoint to manage uploaded consultation documents (medical files).
    Enforces secure 10MB limits, checks extensions, and returns progress handles.
    """
    def get(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)
        
        if booking.user != request.user and booking.appointment.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        files_qs = booking.meeting_files.select_related('uploaded_by').order_by('created_at')
        files_list = [{
            'id': f.id,
            'file_name': f.file_name,
            'file_url': f.file.url,
            'file_size': f"{round(f.file_size / 1024, 1)} KB",
            'uploaded_by': f.uploaded_by.get_full_name(),
            'uploaded_by_role': f.uploaded_by.role,
            'created_at': f.created_at.strftime('%I:%M %p')
        } for f in files_qs]
        
        return JsonResponse({'files': files_list})

    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)
        
        if booking.user != request.user and booking.appointment.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        # Enforce 10MB limit
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File size exceeds 10MB limit'}, status=400)

        # Extension check
        ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
        allowed = ['pdf', 'png', 'jpg', 'jpeg']
        if ext not in allowed:
            return JsonResponse({'error': f'Unsupported file type. Allowed: {", ".join(allowed)}'}, status=400)

        f = MeetingFile.objects.create(
            booking=booking,
            uploaded_by=request.user,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type
        )
        
        return JsonResponse({
            'status': 'success',
            'file': {
                'id': f.id,
                'file_name': f.file_name,
                'file_url': f.file.url,
                'file_size': f"{round(f.file_size / 1024, 1)} KB",
                'uploaded_by': f.uploaded_by.get_full_name(),
                'created_at': f.created_at.strftime('%I:%M %p')
            }
        })


class UpdateMeetingStatusView(LoginRequiredMixin, View):
    """
    Endpoint for doctors to update meeting status (waiting -> active -> ended).
    """
    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)
        
        if booking.appointment.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        import json
        try:
            data = json.loads(request.body)
            status = data.get('status')
        except Exception:
            status = request.POST.get('status')

        if status not in ['waiting', 'active', 'ended']:
            return JsonResponse({'error': 'Invalid status value'}, status=400)

        booking.meeting_status = status
        booking.save(update_fields=['meeting_status'])
        
        return JsonResponse({'status': 'success', 'meeting_status': booking.meeting_status})


class SaveMeetingNotesView(LoginRequiredMixin, View):
    """
    Endpoint for doctors to save meeting notes dynamically.
    """
    def post(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)
        
        if booking.appointment.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        import json
        try:
            data = json.loads(request.body)
            notes = data.get('notes', '').strip()
        except Exception:
            notes = request.POST.get('notes', '').strip()

        booking.meeting_notes = notes
        booking.save(update_fields=['meeting_notes'])
        
        return JsonResponse({'status': 'success', 'message': 'Notes saved successfully'})
