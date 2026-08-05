"""
Doctor Management Views.
Handles doctor list, public profile, profile editing, qualifications,
experience, clinics, fee structure, documents, vacations, and slots.
"""

import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, TemplateView, CreateView, UpdateView

from accounts.models import User
from appointment.decorators import user_is_doctor
from appointment.models import (
    Appointment, DoctorProfile, DoctorQualification, DoctorExperience,
    DoctorClinic, DoctorFeeStructure, DoctorDocument, DoctorVacation,
    DoctorSlot, DEPARTMENT_CHOICES, Review, TakeAppointment
)
from appointment.doctor_forms import (
    DoctorProfileBasicForm, DoctorQualificationForm, DoctorExperienceForm,
    DoctorClinicForm, DoctorFeeStructureForm, DoctorDocumentForm,
    DoctorVacationForm, DoctorSlotForm,
)

LOGIN_URL = reverse_lazy('accounts:login')


# ============================================================================
# Doctor List / Directory (Public)
# ============================================================================

class DoctorListView(ListView):
    """Premium doctor directory with search, filter, and sort."""
    model = DoctorProfile
    template_name = 'appointment/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 12

    def get_queryset(self):
        # Only show NMC-verified doctors in the public directory
        qs = DoctorProfile.objects.select_related('user').filter(
            verification_status='verified',
            is_verified=True,
        ).order_by('-rating', '-patients_treated')

        q = self.request.GET.get('q', '').strip()
        department = self.request.GET.get('department', '').strip()
        city = self.request.GET.get('city', '').strip()
        experience = self.request.GET.get('experience', '').strip()
        gender = self.request.GET.get('gender', '').strip()
        availability = self.request.GET.get('availability', '').strip()
        sort = self.request.GET.get('sort', '').strip()

        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(specialization__icontains=q) |
                Q(hospital__icontains=q) |
                Q(qualification__icontains=q)
            )
        if department:
            qs = qs.filter(specialization__iexact=department)
        if city:
            qs = qs.filter(city__icontains=city)
        if gender:
            qs = qs.filter(user__gender=gender)
        if experience == '0-5':
            qs = qs.filter(experience_years__lte=5)
        elif experience == '5-10':
            qs = qs.filter(experience_years__gte=5, experience_years__lte=10)
        elif experience == '10+':
            qs = qs.filter(experience_years__gte=10)
        if availability == 'available':
            ids = [d.pk for d in qs if d.is_available_now]
            qs = qs.filter(pk__in=ids)
        if sort == 'rating':
            qs = qs.order_by('-rating')
        elif sort == 'experience':
            qs = qs.order_by('-experience_years')
        elif sort == 'fee_low':
            qs = qs.order_by('consultation_fee')
        elif sort == 'fee_high':
            qs = qs.order_by('-consultation_fee')
        elif sort == 'patients':
            qs = qs.order_by('-patients_treated')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dept_choices'] = DEPARTMENT_CHOICES
        verified_qs = DoctorProfile.objects.filter(verification_status='verified', is_verified=True)
        context['total_doctors'] = verified_qs.count()
        context['available_count'] = sum(1 for d in verified_qs if d.is_available_now)
        context['current_filters'] = {
            'q': self.request.GET.get('q', ''),
            'department': self.request.GET.get('department', ''),
            'city': self.request.GET.get('city', ''),
            'experience': self.request.GET.get('experience', ''),
            'gender': self.request.GET.get('gender', ''),
            'availability': self.request.GET.get('availability', ''),
            'sort': self.request.GET.get('sort', ''),
        }
        return context


# ============================================================================
# Doctor Public Profile (Anyone can view)
# ============================================================================

class DoctorPublicProfileView(View):
    """Full public doctor profile with stats, reviews, timelines, and slots."""
    template_name = 'appointment/doctor_public_profile.html'

    def get(self, request, pk, *args, **kwargs):
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        reviews = Review.objects.filter(
            booking__appointment__user=doctor.user,
            is_approved=True
        ).select_related('booking__user').order_by('-created_at')

        sort = request.GET.get('sort', 'recent')
        if sort == 'highest':
            reviews = reviews.order_by('-rating', '-created_at')
        elif sort == 'lowest':
            reviews = reviews.order_by('rating', '-created_at')

        # Available slots for next 7 days
        today = timezone.localdate()
        available_slots_by_day = {}
        for i in range(7):
            day = today + timedelta(days=i)
            weekday = day.weekday()
            day_slots = doctor.slots.filter(weekday=weekday, is_active=True)
            available = [s for s in day_slots if s.is_available_on(day)]
            if available:
                available_slots_by_day[day] = available

        context = {
            'doctor': doctor,
            'reviews': reviews,
            'reviews_count': reviews.count(),
            'avg_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'qualifications': doctor.qualifications.all(),
            'experiences': doctor.experiences.all(),
            'clinics': doctor.clinics.all(),
            'documents': doctor.documents.filter(is_verified=True),
            'available_slots_by_day': available_slots_by_day,
            'sort': sort,
            'dept_choices': dict(DEPARTMENT_CHOICES),
            'can_book': request.user.is_authenticated and getattr(request.user, 'role', '') == 'patient',
        }
        # Fee structure
        try:
            context['fee_structure'] = doctor.fee_structure
        except DoctorFeeStructure.DoesNotExist:
            context['fee_structure'] = None

        return render(request, self.template_name, context)


# ============================================================================
# Doctor Profile Edit (Doctor-only, tabbed)
# ============================================================================

class DoctorProfileEditView(LoginRequiredMixin, View):
    """Tabbed doctor profile editing page."""
    template_name = 'appointment/doctor_profile_edit.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def _get_forms(self, request, doctor):
        """Return all sub-forms for the edit page."""
        post = request.POST if request.method == 'POST' else None
        files = request.FILES if request.method == 'POST' else None
        return {
            'profile_form': DoctorProfileBasicForm(post, files, instance=doctor),
            'qual_form': DoctorQualificationForm(prefix='qual'),
            'exp_form': DoctorExperienceForm(prefix='exp'),
            'clinic_form': DoctorClinicForm(prefix='clinic'),
            'vacation_form': DoctorVacationForm(prefix='vacation'),
            'slot_form': DoctorSlotForm(prefix='slot'),
        }

    def get(self, request, *args, **kwargs):
        doctor = get_object_or_404(DoctorProfile, user=request.user)
        forms = self._get_forms(request, doctor)
        # Fee structure
        try:
            fee_form = DoctorFeeStructureForm(instance=doctor.fee_structure, prefix='fee')
        except DoctorFeeStructure.DoesNotExist:
            fee_form = DoctorFeeStructureForm(prefix='fee')

        return render(request, self.template_name, {
            'doctor': doctor,
            'fee_form': fee_form,
            **forms,
            'qualifications': doctor.qualifications.all(),
            'experiences': doctor.experiences.all(),
            'clinics': doctor.clinics.all(),
            'documents': doctor.documents.all(),
            'vacations': doctor.vacations.filter(end_date__gte=timezone.localdate()),
            'slots': doctor.slots.all().order_by('weekday', 'start_time'),
        })

    def post(self, request, *args, **kwargs):
        doctor = get_object_or_404(DoctorProfile, user=request.user)
        action = request.POST.get('action', 'profile')

        if action == 'profile':
            form = DoctorProfileBasicForm(request.POST, request.FILES, instance=doctor)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
            else:
                messages.error(request, 'Please fix the errors below.')

        elif action == 'add_qualification':
            form = DoctorQualificationForm(request.POST, prefix='qual')
            if form.is_valid():
                q = form.save(commit=False)
                q.doctor = doctor
                q.save()
                messages.success(request, 'Qualification added!')
            else:
                messages.error(request, 'Invalid qualification data.')

        elif action == 'add_experience':
            form = DoctorExperienceForm(request.POST, prefix='exp')
            if form.is_valid():
                e = form.save(commit=False)
                e.doctor = doctor
                e.save()
                messages.success(request, 'Experience added!')
            else:
                messages.error(request, 'Invalid experience data.')

        elif action == 'add_clinic':
            form = DoctorClinicForm(request.POST, prefix='clinic')
            if form.is_valid():
                c = form.save(commit=False)
                c.doctor = doctor
                c.save()
                messages.success(request, 'Clinic added!')
            else:
                messages.error(request, 'Invalid clinic data.')

        elif action == 'update_fees':
            try:
                fee_instance = doctor.fee_structure
                fee_form = DoctorFeeStructureForm(request.POST, instance=fee_instance, prefix='fee')
            except DoctorFeeStructure.DoesNotExist:
                fee_form = DoctorFeeStructureForm(request.POST, prefix='fee')
            if fee_form.is_valid():
                fee = fee_form.save(commit=False)
                fee.doctor = doctor
                fee.save()
                messages.success(request, 'Fee structure updated!')
            else:
                messages.error(request, 'Invalid fee data.')

        elif action == 'upload_document':
            doc_form = DoctorDocumentForm(request.POST, request.FILES)
            if doc_form.is_valid():
                doc = doc_form.save(commit=False)
                doc.doctor = doctor
                doc.save()
                messages.success(request, 'Document uploaded for verification!')
            else:
                messages.error(request, 'Invalid document.')

        elif action == 'add_vacation':
            form = DoctorVacationForm(request.POST, prefix='vacation')
            if form.is_valid():
                v = form.save(commit=False)
                v.doctor = doctor
                v.save()
                messages.success(request, 'Vacation blocked successfully!')
            else:
                messages.error(request, 'Invalid vacation dates.')

        elif action == 'add_slot':
            form = DoctorSlotForm(request.POST, prefix='slot')
            if form.is_valid():
                s = form.save(commit=False)
                s.doctor = doctor
                s.save()
                messages.success(request, 'Slot created!')
            else:
                messages.error(request, 'Invalid slot data.')

        return redirect('appointment:doctor-profile-edit')


# ============================================================================
# Delete Sub-Items (AJAX-friendly POST)
# ============================================================================

class DoctorQualificationDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        q = get_object_or_404(DoctorQualification, pk=pk, doctor__user=request.user)
        q.delete()
        messages.success(request, 'Qualification removed.')
        return redirect('appointment:doctor-profile-edit')


class DoctorExperienceDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        e = get_object_or_404(DoctorExperience, pk=pk, doctor__user=request.user)
        e.delete()
        messages.success(request, 'Experience removed.')
        return redirect('appointment:doctor-profile-edit')


class DoctorClinicDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        c = get_object_or_404(DoctorClinic, pk=pk, doctor__user=request.user)
        c.delete()
        messages.success(request, 'Clinic removed.')
        return redirect('appointment:doctor-profile-edit')


class DoctorDocumentDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        doc = get_object_or_404(DoctorDocument, pk=pk, doctor__user=request.user)
        doc.delete()
        messages.success(request, 'Document removed.')
        return redirect('appointment:doctor-profile-edit')


class DoctorVacationDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        v = get_object_or_404(DoctorVacation, pk=pk, doctor__user=request.user)
        v.delete()
        messages.success(request, 'Vacation block removed.')
        return redirect('appointment:doctor-profile-edit')


class DoctorSlotDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        s = get_object_or_404(DoctorSlot, pk=pk, doctor__user=request.user)
        s.delete()
        messages.success(request, 'Slot removed.')
        return redirect('appointment:doctor-profile-edit')


# ============================================================================
# AJAX: Slot Availability for a Doctor on a Given Date
# ============================================================================

class DoctorSlotAvailabilityAPIView(View):
    """Returns available slots for a doctor on a specific date (AJAX)."""

    def get(self, request, pk, *args, **kwargs):
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        date_str = request.GET.get('date', '')
        try:
            from datetime import date as date_cls
            query_date = date_cls.fromisoformat(date_str)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid date'}, status=400)

        weekday = query_date.weekday()
        slots = doctor.slots.filter(weekday=weekday, is_active=True)

        result = []
        for slot in slots:
            available = slot.is_available_on(query_date)
            result.append({
                'id': slot.pk,
                'session': slot.session,
                'session_label': slot.get_session_display(),
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'is_online': slot.is_online,
                'available': available,
                'capacity': slot.capacity,
                'booked': slot.booked_count_on(query_date),
            })

        return JsonResponse({'date': date_str, 'slots': result})
