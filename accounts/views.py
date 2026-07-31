import uuid
import random
import re
import threading
from datetime import timedelta
from django.contrib import auth, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode, url_has_allowed_host_and_scheme
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views import View
from django.views.generic import CreateView, FormView, RedirectView
from django.urls import reverse
from django.conf import settings

from accounts.forms import (
    UnifiedRegistrationForm,
    DoctorRegistrationForm,
    PatientRegistrationForm,
    UserLoginForm,
    validate_strong_password,
)
from accounts.models import User, EmailVerification, PhoneOTP, OTPCode
from accounts.services import OTPService

# ---------------------------------------------------------------------------
# Helper functions for stubbing Email & SMS deliveries
# ---------------------------------------------------------------------------

def send_verification_email(user, request=None):
    """
    Generates a verification token and sends the email verification link.
    Called in a background thread so it never blocks the request cycle.
    """
    verification = EmailVerification.objects.create(user=user)

    if request:
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        link = f"{protocol}://{domain}{reverse('accounts:verify-email', kwargs={'token': verification.token})}"
    else:
        link = f"/verify-email/{verification.token}/"

    # Try HTML welcome+verify email first
    try:
        context = {
            'user': user,
            'first_name': user.first_name or user.username or 'User',
            'verify_link': link,
            'login_link': (f"{request.scheme}://{request.get_host()}/login/" if request else '/login/'),
        }
        html_content = render_to_string('emails/welcome_verify.html', context)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject="Welcome to DocMed 🎉 – Verify Your Email",
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        # Fallback to plain text
        send_mail(
            subject="Welcome to DocMed – Verify Your Email",
            message=(
                f"Hello {user.first_name or 'User'},\n\n"
                f"Welcome to DocMed! Please verify your email:\n{link}\n\n"
                f"This link expires in 24 hours."
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
            recipient_list=[user.email],
            fail_silently=True,
        )
    print(f"\n[EMAIL SERVICE] Welcome/Verify email sent to {user.email}: {link}\n")


def send_welcome_email_background(user, request=None):
    """Fire-and-forget: send welcome+verify email in a daemon thread."""
    def _send():
        try:
            send_verification_email(user, request)
        except Exception as exc:
            print(f"[EMAIL SERVICE] Background send failed: {exc}")
    t = threading.Thread(target=_send, daemon=True)
    t.start()


def send_login_notification_background(user, request):
    """Fire-and-forget: send login-detected email in a daemon thread."""
    def _send():
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
            ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR', 'Unknown')
            ua = request.META.get('HTTP_USER_AGENT', 'Unknown')
            login_time = timezone.localtime(timezone.now()).strftime('%B %d, %Y at %I:%M %p')
            context = {
                'user': user,
                'first_name': user.first_name or user.username or 'User',
                'login_time': login_time,
                'ip_address': ip,
                'user_agent': ua,
            }
            try:
                html_content = render_to_string('emails/login_notification.html', context)
                text_content = strip_tags(html_content)
                msg = EmailMultiAlternatives(
                    subject="New Login Detected – DocMed 🔐",
                    body=text_content,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
                    to=[user.email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
            except Exception:
                send_mail(
                    subject="New Login Detected – DocMed",
                    message=(
                        f"Hi {user.first_name or 'User'},\n\n"
                        f"A new login was detected on your DocMed account.\n"
                        f"Time: {login_time}\nIP: {ip}\nDevice: {ua}\n\n"
                        f"If this wasn't you, please reset your password immediately."
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            print(f"\n[EMAIL SERVICE] Login notification sent to {user.email}\n")
        except Exception as exc:
            print(f"[EMAIL SERVICE] Login notification failed: {exc}")
    t = threading.Thread(target=_send, daemon=True)
    t.start()


def send_reset_email(user, link):
    """Sends password reset link."""
    subject = "Reset Your DocMed Password"
    message = (
        f"Hello {user.first_name},\n\n"
        f"We received a request to reset your password. Click the link below to set a new password:\n{link}\n\n"
        f"If you did not request this, please ignore this email."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
        recipient_list=[user.email],
        fail_silently=True,
    )
    print(f"\n[PASSWORD RESET EMAIL] Reset link sent to {user.email}: {link}\n")

# ---------------------------------------------------------------------------
# Base registration view
# ---------------------------------------------------------------------------
# Registration views
# ---------------------------------------------------------------------------

class RegisterView(CreateView):
    """
    Single unified registration view allowing users to register as Patient or Doctor.
    Admin registration is strictly prohibited.
    """
    model = User
    form_class = UnifiedRegistrationForm
    template_name = 'accounts/register.html'
    extra_context = {'title': 'Register'}

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return self._redirect_authenticated(self.request.user)
        return super().dispatch(request, *args, **kwargs)

    def _redirect_authenticated(self, user):
        if user.is_superuser or user.is_staff:
            return redirect('appointment:admin-dashboard')
        elif getattr(user, 'role', '') == 'doctor':
            return redirect('appointment:doctor-dashboard')
        return redirect('appointment:patient-dashboard')

    def get_initial(self):
        initial = super().get_initial()
        role = self.request.GET.get('role', '').lower()
        if role in ['patient', 'doctor']:
            initial['role'] = role
        return initial

    def form_valid(self, form):
        user = form.save(commit=False)
        password = form.cleaned_data.get('password1')
        user.set_password(password)
        user.is_active = True
        user.save()

        # Re-save form so save() executes profile creation
        form.save(commit=True)

        try:
            from allauth.account.models import EmailAddress
            EmailAddress.objects.create(
                user=user,
                email=user.email,
                primary=True,
                verified=False,
            )
        except Exception:
            pass

        send_welcome_email_background(user, self.request)

        # Auto-login after registration
        auth.login(self.request, user, backend='accounts.backends.MultiFieldBackend')
        self.request.session.cycle_key()
        self.request.session['show_registration_success'] = True
        self.request.session['registration_role'] = user.role
        self.request.session['email_unverified'] = True

        messages.success(self.request, f'Registration Successful 🎉 Welcome to DocMed, {user.first_name or user.username}!')
        return self._redirect_authenticated(user)


class RegisterPatientView(RedirectView):
    """Backward compatibility redirect to unified registration page."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('accounts:register') + '?role=patient'


class RegisterDoctorView(RedirectView):
    """Backward compatibility redirect to unified registration page."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('accounts:register') + '?role=doctor'

# ---------------------------------------------------------------------------
# AJAX Live Validation Checks
# ---------------------------------------------------------------------------

class CheckUsernameView(View):
    def get(self, request, *args, **kwargs):
        username = request.GET.get('username', '').strip()
        if not username:
            return JsonResponse({'exists': False, 'valid': False, 'message': 'Username is empty'})
        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'exists': exists, 'valid': True})


class CheckEmailView(View):
    def get(self, request, *args, **kwargs):
        email = request.GET.get('email', '').strip()
        if not email:
            return JsonResponse({'exists': False, 'valid': False, 'message': 'Email is empty'})
        exists = User.objects.filter(email__iexact=email).exists()
        return JsonResponse({'exists': exists, 'valid': True})

# ---------------------------------------------------------------------------
# Custom Email Verification View
# ---------------------------------------------------------------------------

class VerifyEmailView(View):
    def get(self, request, token, *args, **kwargs):
        try:
            verification = EmailVerification.objects.get(token=token)
        except (EmailVerification.DoesNotExist, ValueError):
            messages.error(request, 'Invalid or broken verification token.')
            return redirect('accounts:login')

        if verification.is_verified:
            messages.info(request, 'This email address is already verified. Please sign in.')
            return redirect('accounts:login')

        if verification.is_expired():
            messages.error(request, 'This verification link has expired. Please register again.')
            # Optionally clean up inactive user
            user = verification.user
            if not user.is_active:
                user.delete()
            return redirect('accounts:login')

        # Activate user
        user = verification.user
        user.is_active = True
        user.save()

        # Mark verification token as used
        verification.is_verified = True
        verification.save()

        # Update allauth EmailAddress verified status
        try:
            from allauth.account.models import EmailAddress
            email_addr, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={'primary': True, 'verified': True}
            )
            if not email_addr.verified:
                email_addr.verified = True
                email_addr.save(update_fields=['verified'])
        except Exception:
            pass

        messages.success(request, 'Email verified successfully! ✅ All features are now unlocked.')

        # Clear verification banner session flag if user is logged in
        if request.user.is_authenticated and request.user == user:
            request.session.pop('email_unverified', None)
            return redirect('appointment:patient-bookings')

        return redirect('/login?verified=success')

# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

class LoginView(FormView):
    """
    Single unified login view for all users (Patient, Doctor, Admin).
    Supports Email/Username/Phone + Password and Google Sign In.
    Redirects dynamically based on user role upon successful login.
    """
    form_class = UserLoginForm
    template_name = 'accounts/login.html'
    extra_context = {'title': 'Login'}

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        next_url = self.request.GET.get('next', '').strip()
        if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={self.request.get_host()}):
            return next_url

        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse('appointment:admin-dashboard')
        elif getattr(user, 'role', '') == 'doctor':
            return reverse('appointment:doctor-dashboard')
        elif getattr(user, 'role', '') == 'patient':
            return reverse('appointment:patient-dashboard')
        return '/'

    def form_valid(self, form):
        user = form.get_user()
        auth.login(self.request, user, backend='accounts.backends.MultiFieldBackend')

        # Rotate session key to prevent session fixation attacks
        self.request.session.cycle_key()

        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        try:
            from allauth.account.models import EmailAddress
            ea = EmailAddress.objects.filter(user=user, primary=True).first()
            if ea and not ea.verified:
                self.request.session['email_unverified'] = True
        except Exception:
            pass

        send_login_notification_background(user, self.request)
        messages.success(self.request, f"Welcome back, {user.first_name or user.username}! 👋")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class LogoutView(RedirectView):
    """Log the user out and redirect to home."""
    url = '/'

    def get(self, request, *args, **kwargs):
        auth.logout(request)
        request.session.flush()
        messages.success(request, 'Logout successful! Hope to see you again soon.')
        return redirect('/')


class AdminLoginView(RedirectView):
    """Backward compatibility redirect to unified login view."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('accounts:login')


class DoctorLoginView(RedirectView):
    """Backward compatibility redirect to unified login view."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('accounts:login')


class PatientLoginView(RedirectView):
    """Backward compatibility redirect to unified login view."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('accounts:login')

# ---------------------------------------------------------------------------
# Custom OTP Login views (Phone SMS Based)
# ---------------------------------------------------------------------------

class RequestOTPView(View):
    """View to request OTP code via SMS."""
    template_name = 'accounts/otp_request.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        phone_number = request.POST.get('phone_number', '').strip()
        if not phone_number:
            messages.error(request, 'Please provide a valid registered phone number.')
            return render(request, self.template_name)

        success, msg = OTPService.send_otp(phone_number)
        if success:
            messages.success(request, msg)
            return redirect(f"{reverse('accounts:otp-verify')}?phone_number={phone_number}")
        else:
            messages.error(request, msg)
            return render(request, self.template_name, {'phone_number': phone_number})


class VerifyOTPView(View):
    """View to verify SMS OTP code and log the user in."""
    template_name = 'accounts/otp_verify.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')
        phone_number = request.GET.get('phone_number', '')
        return render(request, self.template_name, {'phone_number': phone_number})

    def post(self, request, *args, **kwargs):
        phone_number = request.POST.get('phone_number', '').strip()
        code = request.POST.get('code', '').strip()

        if not phone_number or not code:
            messages.error(request, 'All fields are required.')
            return render(request, self.template_name, {'phone_number': phone_number})

        success, msg = OTPService.verify_otp(phone_number, code)
        if success:
            try:
                user = User.objects.get(phone_number=phone_number)
                
                # Make active and mark verified since they successfully proved ownership of phone
                if not user.is_active:
                    user.is_active = True
                    user.save(update_fields=['is_active'])
                    
                # Update allauth EmailAddress to verified status if email matches user
                try:
                    from allauth.account.models import EmailAddress
                    email_addr, created = EmailAddress.objects.get_or_create(
                        user=user,
                        email=user.email,
                        defaults={'primary': True, 'verified': True}
                    )
                    if not email_addr.verified:
                        email_addr.verified = True
                        email_addr.save(update_fields=['verified'])
                except Exception:
                    pass

                # Login
                auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Verification successful! Welcome back.')
                
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                
                # Redirect based on user role
                if user.is_superuser or user.is_staff:
                    return redirect('appointment:admin-dashboard')
                elif user.role == 'doctor':
                    return redirect('appointment:doctor-appointment')
                else:
                    return redirect('appointment:patient-bookings')
            except User.DoesNotExist:
                messages.error(request, 'User registration error.')
        else:
            messages.error(request, msg)

        return render(request, self.template_name, {'phone_number': phone_number})

# ---------------------------------------------------------------------------
# Custom Forgot Password & Reset Password views
# ---------------------------------------------------------------------------

class ForgotPasswordView(View):
    """View to request password reset instructions via email or phone."""
    template_name = 'registration/password_reset_form.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email_or_phone = request.POST.get('email_or_phone', '').strip()
        if not email_or_phone:
            messages.error(request, 'Please enter your registered email address or phone number.')
            return render(request, self.template_name)

        if '@' in email_or_phone:
            # Handle reset via email
            try:
                user = User.objects.get(email__iexact=email_or_phone)
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
                link = f"{protocol}://{domain}{reverse('accounts:password_reset_confirm_custom', kwargs={'uidb64': uidb64, 'token': token})}"
                
                send_reset_email(user, link)
                messages.success(request, 'Password reset instructions have been sent to your registered email.')
            except User.DoesNotExist:
                # Keep user guessing to prevent user enumeration security issues
                messages.success(request, 'Password reset instructions have been sent to your registered email.')
        else:
            # Handle reset via phone number
            try:
                user = User.objects.get(phone_number=email_or_phone)
                success, msg = OTPService.send_otp(user.phone_number)
                if success:
                    messages.success(request, 'A 6-digit verification code has been sent to your registered phone number.')
                    return redirect(f"{reverse('accounts:password_reset_verify_phone')}?phone_number={user.phone_number}")
                else:
                    messages.error(request, msg)
            except User.DoesNotExist:
                messages.success(request, 'Verification code has been sent if phone number is registered.')

        return render(request, self.template_name)


class PasswordResetVerifyPhoneView(View):
    """Verifies the phone OTP for password reset."""
    template_name = 'registration/password_reset_verify_phone.html'

    def get(self, request, *args, **kwargs):
        phone_number = request.GET.get('phone_number', '')
        return render(request, self.template_name, {'phone_number': phone_number})

    def post(self, request, *args, **kwargs):
        phone_number = request.POST.get('phone_number', '').strip()
        code = request.POST.get('code', '').strip()

        if not phone_number or not code:
            messages.error(request, 'All fields are required.')
            return render(request, self.template_name, {'phone_number': phone_number})

        success, msg = OTPService.verify_otp(phone_number, code)
        if success:
            request.session['reset_phone_verified'] = phone_number
            return redirect('accounts:password_reset_phone_new')
        else:
            messages.error(request, msg)
            return render(request, self.template_name, {'phone_number': phone_number})


class PasswordResetPhoneNewView(View):
    """Allows user to enter a new password after verifying phone number."""
    template_name = 'registration/password_reset_confirm.html'

    def get(self, request, *args, **kwargs):
        phone_number = request.session.get('reset_phone_verified')
        if not phone_number:
            messages.error(request, 'Verification required.')
            return redirect('accounts:password_reset')
        return render(request, self.template_name, {'validlink': True})

    def post(self, request, *args, **kwargs):
        phone_number = request.session.get('reset_phone_verified')
        if not phone_number:
            messages.error(request, 'Verification expired or missing.')
            return redirect('accounts:password_reset')

        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not password1 or not password2:
            messages.error(request, 'Please fill in all password fields.')
            return render(request, self.template_name, {'validlink': True})

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, self.template_name, {'validlink': True})

        try:
            validate_strong_password(password1)
        except ValidationError as e:
            messages.error(request, e.message)
            return render(request, self.template_name, {'validlink': True})

        try:
            user = User.objects.get(phone_number=phone_number)
            user.set_password(password1)
            user.save()
            
            # Clean session
            del request.session['reset_phone_verified']
            
            messages.success(request, 'Password updated successfully! You can now log in.')
            return redirect('accounts:login')
        except User.DoesNotExist:
            messages.error(request, 'Account registration error.')
            return redirect('accounts:password_reset')


class ResetPasswordConfirmCustomView(View):
    """Handles the custom link reset confirmation from emails."""
    template_name = 'registration/password_reset_confirm.html'

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            return render(request, self.template_name, {'validlink': True})
        else:
            return render(request, self.template_name, {'validlink': False})

    def post(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')

            if not password1 or not password2:
                messages.error(request, 'Please fill in all password fields.')
                return render(request, self.template_name, {'validlink': True})

            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
                return render(request, self.template_name, {'validlink': True})

            try:
                validate_strong_password(password1)
            except ValidationError as e:
                messages.error(request, e.message)
                return render(request, self.template_name, {'validlink': True})

            user.set_password(password1)
            user.save()
            messages.success(request, 'Your password has been reset successfully. You can now log in.')
            return redirect('accounts:login')
        else:
            return render(request, self.template_name, {'validlink': False})


# ---------------------------------------------------------------------------
# Session UX Helper Views
# ---------------------------------------------------------------------------

class ResendVerificationView(View):
    """Resend the email verification link to the currently logged-in user."""

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to resend the verification email.')
            return redirect('accounts:login')
        user = request.user
        # Check if already verified
        try:
            from allauth.account.models import EmailAddress
            ea = EmailAddress.objects.filter(user=user, primary=True).first()
            if ea and ea.verified:
                request.session.pop('email_unverified', None)
                messages.info(request, 'Your email address is already verified.')
                return redirect('appointment:patient-bookings')
        except Exception:
            pass
        # Send fresh verification email in background
        send_welcome_email_background(user, request)
        messages.success(request, 'Verification email resent! Please check your inbox.')
        # Redirect back to where user came from
        next_url = request.META.get('HTTP_REFERER', '/')
        return redirect(next_url)


class DismissVerifyBannerView(View):
    """AJAX POST – clear email_unverified session flag (user dismissed the banner)."""

    def post(self, request, *args, **kwargs):
        request.session.pop('email_unverified', None)
        return JsonResponse({'status': 'ok'})


class DismissRegSuccessView(View):
    """AJAX POST – clear show_registration_success session flag after modal is dismissed."""

    def post(self, request, *args, **kwargs):
        request.session.pop('show_registration_success', None)
        request.session.pop('registration_role', None)
        return JsonResponse({'status': 'ok'})
