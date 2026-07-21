"""
Patient Management Views.
Handles patient profile dashboard, profile editing, medical history,
emergency contacts, and insurance management.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from appointment.decorators import user_is_patient
from appointment.models import (
    PatientProfile, PatientEmergencyContact, PatientInsurance,
    TakeAppointment, Review,
)
from appointment.patient_forms import (
    PatientProfileAdvancedForm, PatientEmergencyContactForm, PatientInsuranceForm,
)

LOGIN_URL = reverse_lazy('accounts:login')


# ============================================================================
# Patient Profile Dashboard
# ============================================================================

class PatientProfileView(LoginRequiredMixin, View):
    """Premium patient profile dashboard."""
    template_name = 'appointment/patient_profile.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(PatientProfile, user=request.user)
        bookings = TakeAppointment.objects.filter(
            user=request.user
        ).select_related('appointment', 'appointment__user__doctor_profile').order_by('-date')

        now = timezone.now()
        upcoming = [b for b in bookings if b.status in ['pending', 'approved', 'rescheduled'] and b.date >= now]
        past = [b for b in bookings if b not in upcoming]

        stats = {
            'total': bookings.count(),
            'completed': bookings.filter(status='completed').count(),
            'upcoming': len(upcoming),
            'cancelled': bookings.filter(status='cancelled').count(),
        }

        insurance_policies = profile.insurance_policies.all()
        emergency_contacts = profile.emergency_contacts.all()

        context = {
            'profile': profile,
            'stats': stats,
            'upcoming_bookings': upcoming[:3],
            'past_bookings': past[:5],
            'emergency_contacts': emergency_contacts,
            'insurance_policies': insurance_policies,
            'calculated_age': profile.calculated_age,
        }
        return render(request, self.template_name, context)


# ============================================================================
# Patient Profile Edit (Tabbed)
# ============================================================================

class PatientProfileEditView(LoginRequiredMixin, View):
    """Tabbed patient profile editing page."""
    template_name = 'appointment/patient_profile_edit.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(PatientProfile, user=request.user)
        context = {
            'profile': profile,
            'profile_form': PatientProfileAdvancedForm(instance=profile),
            'contact_form': PatientEmergencyContactForm(),
            'insurance_form': PatientInsuranceForm(),
            'emergency_contacts': profile.emergency_contacts.all(),
            'insurance_policies': profile.insurance_policies.all(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(PatientProfile, user=request.user)
        action = request.POST.get('action', 'profile')

        if action == 'profile':
            form = PatientProfileAdvancedForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                # Auto-calculate age from DOB if provided
                if profile.date_of_birth:
                    from django.utils import timezone as tz
                    today = tz.localdate()
                    born = profile.date_of_birth
                    profile.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                    profile.save(update_fields=['age'])
                messages.success(request, 'Profile updated successfully!')
            else:
                messages.error(request, 'Please fix the errors below.')

        elif action == 'add_contact':
            form = PatientEmergencyContactForm(request.POST)
            if form.is_valid():
                contact = form.save(commit=False)
                contact.patient = profile
                contact.save()
                messages.success(request, 'Emergency contact added!')
            else:
                messages.error(request, 'Invalid contact data.')

        elif action == 'add_insurance':
            form = PatientInsuranceForm(request.POST, request.FILES)
            if form.is_valid():
                ins = form.save(commit=False)
                ins.patient = profile
                ins.save()
                messages.success(request, 'Insurance policy added!')
            else:
                messages.error(request, 'Invalid insurance data.')

        return redirect('appointment:patient-profile-edit')


# ============================================================================
# Delete Emergency Contact / Insurance
# ============================================================================

class PatientEmergencyContactDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        contact = get_object_or_404(PatientEmergencyContact, pk=pk, patient__user=request.user)
        contact.delete()
        messages.success(request, 'Emergency contact removed.')
        return redirect('appointment:patient-profile-edit')


class PatientInsuranceDeleteView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        ins = get_object_or_404(PatientInsurance, pk=pk, patient__user=request.user)
        ins.delete()
        messages.success(request, 'Insurance policy removed.')
        return redirect('appointment:patient-profile-edit')
