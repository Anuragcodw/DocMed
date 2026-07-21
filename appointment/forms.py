"""
Appointment forms module.

Provides forms for creating appointment slots and booking appointments.
"""

from django import forms

from .models import Appointment, TakeAppointment


# ---------------------------------------------------------------------------
# Helper to bulk-set placeholder attributes on form fields
# ---------------------------------------------------------------------------

def _apply_placeholders(fields, mapping):
    """Apply placeholder attributes to a dict of form fields."""
    for field_name, placeholder in mapping.items():
        if field_name in fields:
            fields[field_name].widget.attrs.update({'placeholder': placeholder})


# ---------------------------------------------------------------------------
# Appointment slot form (used by doctors)
# ---------------------------------------------------------------------------


class CreateAppointmentForm(forms.ModelForm):
    """Form for a doctor to post a new appointment slot."""

    class Meta:
        model = Appointment
        fields = [
            'full_name', 'image', 'department', 'start_time',
            'end_time', 'location', 'hospital_name',
            'qualification_name', 'institute_name',
        ]

    LABELS = {
        'full_name': 'Full Name',
        'image': 'Image',
        'department': 'Department',
        'start_time': 'Start Time',
        'hospital_name': 'Hospital Name',
        'qualification_name': 'Qualification',
        'institute_name': 'Institute',
    }

    PLACEHOLDERS = {
        'full_name': 'Enter Full Name',
        'department': 'Select Your Service',
        'start_time': 'Ex : 9 AM',
        'end_time': 'Ex: 5 PM',
        'location': 'Ex : Uttara, Dhaka',
        'hospital_name': 'Enter Hospital Name',
        'qualification_name': 'Ex : MBBS, BDS',
        'institute_name': 'Ex : DMC',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, label in self.LABELS.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
        _apply_placeholders(self.fields, self.PLACEHOLDERS)


# ---------------------------------------------------------------------------
# Appointment booking form (used by patients)
# ---------------------------------------------------------------------------


class TakeAppointmentForm(forms.ModelForm):
    """Form for a patient to book an appointment with a doctor."""

    class Meta:
        model = TakeAppointment
        fields = ['appointment', 'full_name', 'phone_number', 'message']

    LABELS = {
        'appointment': 'Choose Your Doctor',
        'full_name': 'Full Name',
        'phone_number': 'Phone Number',
        'message': 'Message',
    }

    PLACEHOLDERS = {
        'appointment': 'Choose Your Doctor',
        'full_name': 'Write Your Name',
        'phone_number': 'Enter Phone Number',
        'message': 'Write a short message',
    }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field_name, label in self.LABELS.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
        _apply_placeholders(self.fields, self.PLACEHOLDERS)

    def clean(self):
        cleaned_data = super().clean()
        appointment = cleaned_data.get('appointment')
        
        if appointment:
            # 1. Prevent double booking of the exact same slot
            from .models import TakeAppointment
            active_slot_bookings = TakeAppointment.objects.filter(
                appointment=appointment,
                status__in=['pending', 'approved', 'rescheduled']
            )
            if self.instance and self.instance.pk:
                active_slot_bookings = active_slot_bookings.exclude(pk=self.instance.pk)
                
            if active_slot_bookings.exists():
                raise forms.ValidationError("This operational slot has already been booked by another patient.")
                
            # 2. Prevent the same patient from booking duplicate appointments for the same slot
            if self.user:
                duplicate_user_bookings = TakeAppointment.objects.filter(
                    user=self.user,
                    appointment=appointment,
                    status__in=['pending', 'approved', 'rescheduled']
                )
                if self.instance and self.instance.pk:
                    duplicate_user_bookings = duplicate_user_bookings.exclude(pk=self.instance.pk)
                    
                if duplicate_user_bookings.exists():
                    raise forms.ValidationError("You have already submitted a pending or approved booking for this slot.")
                    
        return cleaned_data

