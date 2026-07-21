"""
Patient Management Forms.
Provides forms for patient profile editing, medical history,
emergency contacts, and insurance.
"""

from django import forms
from appointment.models import PatientProfile, PatientEmergencyContact, PatientInsurance


class PatientProfileAdvancedForm(forms.ModelForm):
    """Extended patient profile form with medical history and lifestyle."""

    class Meta:
        model = PatientProfile
        fields = [
            'photo', 'cover_image', 'gender', 'date_of_birth',
            'blood_group', 'height', 'weight',
            'city', 'state', 'country', 'preferred_language',
            'medical_history', 'past_diseases', 'allergies',
            'current_medications', 'chronic_diseases', 'surgeries', 'family_history',
            'smoking', 'alcohol', 'exercise',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'blood_group': forms.Select(attrs={'class': 'form-control'}),
            'smoking': forms.Select(attrs={'class': 'form-control'}),
            'alcohol': forms.Select(attrs={'class': 'form-control'}),
            'exercise': forms.Select(attrs={'class': 'form-control'}),
            'medical_history': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'List any past or present medical conditions...'
            }),
            'past_diseases': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'List previous diseases...'
            }),
            'allergies': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'List known allergies (medications, food, etc.)...'
            }),
            'current_medications': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'List current medications with dosage...'
            }),
            'chronic_diseases': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Diabetes, Hypertension, Asthma, etc.'
            }),
            'surgeries': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'List previous surgeries with year...'
            }),
            'family_history': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Family history of genetic or chronic conditions...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_fields = [
            'height', 'weight', 'city', 'state', 'country', 'preferred_language',
        ]
        placeholders = {
            'height': "e.g. 175 cm or 5'9\"",
            'weight': 'e.g. 70 kg',
            'city': 'City',
            'state': 'State / Province',
            'country': 'Country',
            'preferred_language': 'e.g. English, Hindi',
        }
        for name in text_fields:
            self.fields[name].widget.attrs['class'] = 'form-control'
            if name in placeholders:
                self.fields[name].widget.attrs['placeholder'] = placeholders[name]


class PatientEmergencyContactForm(forms.ModelForm):
    """Add / edit an emergency contact."""

    class Meta:
        model = PatientEmergencyContact
        fields = ['name', 'relation', 'phone', 'email', 'address', 'is_primary']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact full name'}),
            'relation': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PatientInsuranceForm(forms.ModelForm):
    """Add / edit insurance policy details."""

    class Meta:
        model = PatientInsurance
        fields = [
            'company_name', 'policy_number', 'coverage_amount',
            'expiry_date', 'insurance_card', 'notes'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Star Health Insurance'}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Policy number'}),
            'coverage_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '500000'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any additional notes...'}),
        }
