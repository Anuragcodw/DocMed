"""
Role-based access decorators for DocMed.

doctor_required  — allows only verified doctors (verification_status == 'verified')
                   or admin / staff users.
patient_required — allows only patients or admin / staff users.
admin_required   — allows only superusers or staff members.

Unverified doctors (pending / rejected / suspended) are redirected to the
pending-verification holding page with a status-appropriate message.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

# Re-export for convenience
login_required = login_required


# ── Status messages shown to non-verified doctors ──────────────────────────
_DOCTOR_STATUS_MESSAGES = {
    'pending': (
        'Your account is pending verification. '
        'Our admin team will review your credentials shortly.'
    ),
    'rejected': (
        'Your doctor registration was not approved. '
        'Please check the remarks on your verification page or contact support.'
    ),
    'suspended': (
        'Your doctor account has been suspended. '
        'Please contact admin@docmed.in for assistance.'
    ),
}


def admin_required(function):
    """Allow only authenticated superusers or staff members."""

    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in with administrator credentials.')
            return redirect('accounts:login')
        if request.user.is_superuser or request.user.is_staff:
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Administrator privileges required.')
        return redirect('appointment:home')

    return wrap


def doctor_required(function):
    """
    Permit access only to verified doctors and admin / staff.

    Doctor verification_status must be 'verified'.
    Any other status redirects the doctor to the pending-verification page
    with a clear, human-readable explanation.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')

        # Admin / staff always pass through
        if request.user.is_superuser or request.user.is_staff:
            return function(request, *args, **kwargs)

        if getattr(request.user, 'role', '') == 'doctor':
            profile = getattr(request.user, 'doctor_profile', None)

            # If profile exists, enforce verification
            if profile is not None and profile.verification_status != 'verified':
                msg = _DOCTOR_STATUS_MESSAGES.get(
                    profile.verification_status,
                    'Your account is not yet verified.'
                )
                messages.warning(request, msg)
                return redirect('accounts:doctor_pending_verification')

            # Verified doctor (or no profile yet — allow through)
            return function(request, *args, **kwargs)

        messages.error(request, 'Access denied. Doctor account required.')
        return redirect('appointment:home')

    return wrap


def patient_required(function):
    """
    Allow authenticated Patient users as well as Admin / Staff members.
    Doctors cannot access patient-only views.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')
        if (
            getattr(request.user, 'role', '') == 'patient'
            or request.user.is_superuser
            or request.user.is_staff
        ):
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Patient account required.')
        return redirect('appointment:home')

    return wrap


# ── Backward-compatibility aliases ─────────────────────────────────────────
user_is_doctor  = doctor_required
user_is_patient = patient_required