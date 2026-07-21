from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# Re-export login_required for ease of import
login_required = login_required

def admin_required(function):
    """Allow only authenticated superusers or staff members."""
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in with admin credentials.')
            return redirect('accounts:admin-login')
        if request.user.is_superuser or request.user.is_staff:
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('appointment:home')
    return wrap

def doctor_required(function):
    """Allow only authenticated users with role='doctor'."""
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')
        if request.user.role == 'doctor':
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Doctor account required.')
        return redirect('appointment:home')
    return wrap

def patient_required(function):
    """Allow only authenticated users with role='patient'."""
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')
        if request.user.role == 'patient':
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Patient account required.')
        return redirect('appointment:home')
    return wrap

# Maintain old aliases for backward compatibility if any
user_is_patient = patient_required
user_is_doctor = doctor_required