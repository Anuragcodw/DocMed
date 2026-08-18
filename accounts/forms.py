"""
Account forms module.

Provides registration, login, and profile-update forms.
"""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User

GENDER_CHOICES = (
    ('male', 'Male'),
    ('female', 'Female'),
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _apply_placeholders(fields, mapping):
    """Apply placeholder attributes to a dict of form fields."""
    for field_name, placeholder in mapping.items():
        if field_name in fields:
            fields[field_name].widget.attrs.update({'placeholder': placeholder})


import re
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_strong_password(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValidationError("Password must contain at least one special character.")

# ---------------------------------------------------------------------------
# Registration forms
# ---------------------------------------------------------------------------

REGISTRATION_ROLE_CHOICES = (
    ('patient', 'Patient'),
    ('doctor', 'Doctor'),
)


class UnifiedRegistrationForm(UserCreationForm):
    """
    Single unified registration form where users select their account role
    (Patient or Doctor only). Admin registration is strictly prohibited.
    """
    role = forms.ChoiceField(
        choices=REGISTRATION_ROLE_CHOICES,
        widget=forms.RadioSelect,
        initial='patient',
        label='Register As',
        error_messages={'required': 'Please select your account type (Patient or Doctor).'}
    )

    PLACEHOLDERS = {
        'username': 'Enter Username',
        'first_name': 'Enter First Name',
        'last_name': 'Enter Last Name',
        'email': 'Enter Email',
        'phone_number': 'Enter Phone Number (e.g. +1234567890)',
        'password1': 'Enter Password',
        'password2': 'Confirm Password',
    }

    class Meta:
        model = User
        fields = [
            'role', 'username', 'first_name', 'last_name', 'email',
            'phone_number', 'password1', 'password2', 'gender',
        ]
        error_messages = {
            'username': {
                'required': 'Username is required',
                'unique': 'A user with that username already exists.',
            },
            'first_name': {'required': 'First name is required'},
            'last_name': {'required': 'Last name is required'},
            'gender': {'required': 'Gender is required'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gender'].required = False
        self.fields['username'].label = 'Username'
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email'
        self.fields['phone_number'].label = 'Phone Number'
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'
        for fieldname in ['password1', 'password2']:
            self.fields[fieldname].help_text = None
        _apply_placeholders(self.fields, self.PLACEHOLDERS)

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in ['patient', 'doctor']:
            raise forms.ValidationError('Invalid role. Registration is restricted to Patients and Doctors only.')
        return role

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError('Username can only contain alphanumeric characters, underscores, hyphens, dots, and @.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Please enter a valid email address.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please login or use another email address.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        if not phone_number:
            raise forms.ValidationError('Please enter a valid phone number.')
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone_number):
            raise forms.ValidationError('Please enter a valid phone number (e.g. +1234567890).')
        return phone_number

    def clean_gender(self):
        # Gender is optional — empty string is acceptable
        return self.cleaned_data.get('gender', '')

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if not password:
            raise forms.ValidationError('Password is required.')
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
        return password

    def save(self, commit=True):
        from appointment.models import DoctorProfile, PatientProfile
        user = super(UserCreationForm, self).save(commit=False)
        user.role = self.cleaned_data.get('role', 'patient')
        if commit:
            user.save()
            if user.role == 'doctor':
                DoctorProfile.objects.get_or_create(user=user)
            else:
                PatientProfile.objects.get_or_create(user=user)
        return user


class PatientRegistrationForm(UserCreationForm):
    """Registration form for patient users."""

    PLACEHOLDERS = {
        'username': 'Enter Username',
        'first_name': 'Enter First Name',
        'last_name': 'Enter Last Name',
        'email': 'Enter Email',
        'phone_number': 'Enter Phone Number (e.g. +1234567890)',
        'password1': 'Enter Password',
        'password2': 'Confirm Password',
    }

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'phone_number', 'password1', 'password2', 'gender',
        ]
        error_messages = {
            'username': {
                'required': 'Username is required',
                'unique': 'A user with that username already exists.',
            },
            'first_name': {
                'required': 'First name is required',
                'max_length': 'Name is too long',
            },
            'last_name': {
                'required': 'Last name is required',
                'max_length': 'Last Name is too long',
            },
            'gender': {
                'required': 'Gender is required',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gender'].required = True
        self.fields['username'].label = 'Username'
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email'
        self.fields['phone_number'].label = 'Phone Number'
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'
        for fieldname in ['password1', 'password2']:
            self.fields[fieldname].help_text = None
        _apply_placeholders(self.fields, self.PLACEHOLDERS)

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError('Username can only contain alphanumeric characters, underscores, hyphens, dots, and @.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Please enter a valid email address.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please login or use another email address.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        if not phone_number:
            raise forms.ValidationError('Please enter a valid phone number.')
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone_number):
            raise forms.ValidationError('Please enter a valid phone number (e.g. +1234567890).')
        return phone_number

    def clean_gender(self):
        gender = self.cleaned_data.get('gender')
        if not gender:
            raise forms.ValidationError('Gender is required')
        return gender

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_strong_password(password)
        return password

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.role = 'patient'
        if commit:
            user.save()
        return user


def validate_uploaded_document(file_obj):
    """Validate uploaded document format (PDF, JPG, PNG) and max size (10MB)."""
    if not file_obj:
        return
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValidationError(f'Invalid file format ({ext}). Only PDF, JPG, and PNG documents are accepted.')
    if file_obj.size > 10 * 1024 * 1024:
        raise ValidationError('File size exceeds the maximum limit of 10MB.')


class DoctorRegistrationForm(UserCreationForm):
    """Registration form for doctor users."""

    PLACEHOLDERS = {
        'username': 'Enter Username',
        'first_name': 'Enter First Name',
        'last_name': 'Enter Last Name',
        'email': 'Enter Email',
        'phone_number': 'Enter Phone Number (e.g. +1234567890)',
        'password1': 'Enter Password',
        'password2': 'Confirm Password',
    }

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'phone_number', 'password1', 'password2', 'gender',
        ]
        error_messages = {
            'username': {
                'required': 'Username is required',
                'unique': 'A user with that username already exists.',
            },
            'first_name': {
                'required': 'First name is required',
                'max_length': 'First Name is too long',
            },
            'last_name': {
                'required': 'Last name is required',
                'max_length': 'Last Name is too long',
            },
            'gender': {
                'required': 'Gender is required',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gender'].required = True
        self.fields['username'].label = 'Username'
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email'
        self.fields['phone_number'].label = 'Phone Number'
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'
        for fieldname in ['password1', 'password2']:
            self.fields[fieldname].help_text = None
        _apply_placeholders(self.fields, self.PLACEHOLDERS)

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError('Username can only contain alphanumeric characters, underscores, hyphens, dots, and @.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Please enter a valid email address.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please login or use another email address.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        if not phone_number:
            raise forms.ValidationError('Please enter a valid phone number.')
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone_number):
            raise forms.ValidationError('Please enter a valid phone number (e.g. +1234567890).')
        return phone_number

    def clean_gender(self):
        gender = self.cleaned_data.get('gender')
        if not gender:
            raise forms.ValidationError('Gender is required')
        return gender

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_strong_password(password)
        return password

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.role = 'doctor'
        if commit:
            user.save()
        return user



# ---------------------------------------------------------------------------
# Login form
# ---------------------------------------------------------------------------


class UserLoginForm(forms.Form):
    """Authentication form supporting email, username, or phone number."""

    login_credential = forms.CharField(
        label='Email, Username or Phone',
        max_length=254,
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput,
    )
    remember_me = forms.BooleanField(
        label='Remember Me',
        required=False,
        initial=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        _apply_placeholders(self.fields, {
            'login_credential': 'Enter Username, Email or Phone',
            'password': 'Enter Password',
        })

    def clean(self, *args, **kwargs):
        login_credential = self.cleaned_data.get('login_credential', '').strip()
        password = self.cleaned_data.get('password')

        if login_credential and password:
            # We authenticate using our MultiFieldBackend (passed via username parameter)
            self.user = authenticate(username=login_credential, password=password)
            if self.user is None:
                raise forms.ValidationError('Invalid username/email/phone or password.')
            if not self.user.is_active:
                raise forms.ValidationError('This account is currently inactive. Please confirm your email address first.')

        return super().clean(*args, **kwargs)

    def get_user(self):
        return self.user



# ---------------------------------------------------------------------------
# Profile update forms
# ---------------------------------------------------------------------------


class PatientProfileUpdateForm(forms.ModelForm):
    """Form for patients to update their User details."""

    PLACEHOLDERS = {
        'first_name': 'Enter First Name',
        'last_name': 'Enter Last Name',
        'email': 'Email',
        'phone_number': 'Phone Number',
    }

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'gender']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_placeholders(self.fields, self.PLACEHOLDERS)


class DoctorProfileUpdateForm(forms.ModelForm):
    """Form for doctors to update their User details."""

    PLACEHOLDERS = {
        'first_name': 'Enter First Name',
        'last_name': 'Enter Last Name',
        'email': 'Email',
        'phone_number': 'Phone Number',
    }

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'gender']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_placeholders(self.fields, self.PLACEHOLDERS)


from appointment.models import DoctorProfile, PatientProfile

class DoctorProfileForm(forms.ModelForm):
    """Form for editing rich DoctorProfile details."""

    class Meta:
        model = DoctorProfile
        fields = [
            'photo', 'qualification', 'specialization', 'hospital',
            'city', 'state', 'country', 'full_address',
            'experience_years', 'consultation_fee', 'bio', 'languages',
            'working_days', 'license_number', 'opening_time', 'closing_time',
            'online_consultation', 'offline_consultation'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'full_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'opening_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_placeholders(self.fields, {
            'qualification': 'e.g. MBBS, FCPS',
            'hospital': 'Hospital or Clinic Name',
            'city': 'e.g. Dhaka',
            'state': 'e.g. Dhaka Division',
            'country': 'e.g. Bangladesh',
            'experience_years': 'Years of Experience',
            'consultation_fee': 'Consultation Fee',
            'languages': 'Languages Spoken (comma-separated)',
            'working_days': 'Working Days (comma-separated, e.g. Mon, Wed, Fri)',
            'license_number': 'Medical License Registration Number',
        })


class PatientProfileForm(forms.ModelForm):
    """Form for editing rich PatientProfile details."""

    class Meta:
        model = PatientProfile
        fields = [
            'photo', 'city', 'state', 'country', 'emergency_contact',
            'age', 'date_of_birth', 'blood_group', 'height', 'weight',
            'medical_history', 'past_diseases', 'allergies',
            'current_medications', 'insurance_details', 'preferred_language'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'medical_history': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'past_diseases': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'allergies': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'current_medications': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'insurance_details': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_placeholders(self.fields, {
            'city': 'e.g. Chittagong',
            'state': 'e.g. Division',
            'country': 'e.g. Bangladesh',
            'emergency_contact': 'Emergency Contact Number',
            'age': 'Age',
            'blood_group': 'e.g. A+',
            'height': 'e.g. 175 cm',
            'weight': 'e.g. 70 kg',
            'preferred_language': 'e.g. English, Bengali',
        })