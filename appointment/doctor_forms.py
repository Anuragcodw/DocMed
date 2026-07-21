"""
Doctor Management Forms.
Provides forms for doctor profile editing, qualifications, experience,
clinics, fee structure, document upload, vacations, and slots.
"""

from django import forms
from appointment.models import (
    DoctorProfile, DoctorQualification, DoctorExperience,
    DoctorClinic, DoctorFeeStructure, DoctorDocument,
    DoctorVacation, DoctorSlot,
    DEPARTMENT_CHOICES,
)


LANGUAGE_CHOICES = [
    ('English', 'English'), ('Hindi', 'Hindi'), ('Punjabi', 'Punjabi'),
    ('Tamil', 'Tamil'), ('Gujarati', 'Gujarati'), ('Marathi', 'Marathi'),
    ('Bengali', 'Bengali'), ('Urdu', 'Urdu'), ('Telugu', 'Telugu'),
    ('Kannada', 'Kannada'), ('Malayalam', 'Malayalam'), ('Odia', 'Odia'),
    ('Assamese', 'Assamese'), ('Sindhi', 'Sindhi'), ('Kashmiri', 'Kashmiri'),
]


class DoctorProfileBasicForm(forms.ModelForm):
    """Form for editing core DoctorProfile details."""

    class Meta:
        model = DoctorProfile
        fields = [
            'photo', 'cover_image', 'qualification', 'specialization',
            'hospital', 'experience_years', 'bio', 'about', 'languages',
            'license_number', 'medical_registration_number',
            'city', 'state', 'country', 'full_address',
            'opening_time', 'closing_time', 'working_days',
            'consultation_fee', 'online_consultation', 'offline_consultation', 'emergency',
            'social_facebook', 'social_twitter', 'social_linkedin',
            'social_instagram', 'social_website',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Short biography...'}),
            'about': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Detailed about section for your public profile...'}),
            'full_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'opening_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput)):
                existing_class = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_class:
                    field.widget.attrs['class'] = (existing_class + ' form-control').strip()


class DoctorQualificationForm(forms.ModelForm):
    """Add/edit a single qualification entry."""

    class Meta:
        model = DoctorQualification
        fields = ['degree', 'institute', 'year', 'description']
        widgets = {
            'degree': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MBBS, MD, MS'}),
            'institute': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Institution name'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Year of completion'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description'}),
        }


class DoctorExperienceForm(forms.ModelForm):
    """Add/edit a single experience entry."""

    class Meta:
        model = DoctorExperience
        fields = ['hospital_name', 'designation', 'start_date', 'end_date', 'is_current', 'description']
        widgets = {
            'hospital_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hospital / Clinic name'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Surgeon'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DoctorClinicForm(forms.ModelForm):
    """Add/edit a clinic entry."""

    class Meta:
        model = DoctorClinic
        fields = [
            'name', 'clinic_type', 'address', 'city', 'state', 'country',
            'phone', 'working_days', 'opening_time', 'closing_time', 'is_primary'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Clinic / Hospital name'}),
            'clinic_type': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'working_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mon,Wed,Fri'}),
            'opening_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DoctorFeeStructureForm(forms.ModelForm):
    """Edit the doctor's full fee breakdown."""

    class Meta:
        model = DoctorFeeStructure
        fields = [
            'currency', 'clinic_fee', 'video_fee', 'emergency_fee',
            'followup_fee', 'discount_percent', 'free_followup_days', 'notes'
        ]
        widgets = {
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'clinic_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'video_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'emergency_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'followup_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'free_followup_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Additional fee notes...'}),
        }


class DoctorDocumentForm(forms.ModelForm):
    """Upload a verification document."""

    class Meta:
        model = DoctorDocument
        fields = ['doc_type', 'title', 'file']
        widgets = {
            'doc_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Document title'}),
        }


class DoctorVacationForm(forms.ModelForm):
    """Block dates for vacation / emergency leave."""

    class Meta:
        model = DoctorVacation
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'is_recurring_weekly']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason (optional)'}),
            'is_recurring_weekly': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError("End date must be after start date.")
        return cleaned_data


class DoctorSlotForm(forms.ModelForm):
    """Create a recurring weekly slot."""

    class Meta:
        model = DoctorSlot
        fields = ['session', 'weekday', 'start_time', 'end_time', 'capacity', 'is_online', 'effective_from', 'effective_until']
        widgets = {
            'session': forms.Select(attrs={'class': 'form-control'}),
            'weekday': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_online': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'effective_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'effective_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned_data
