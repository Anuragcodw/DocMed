import os
import uuid
import requests
from django.core.files.base import ContentFile
from django.shortcuts import redirect
from django.urls import reverse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from accounts.models import User
from appointment.models import PatientProfile


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for allauth to:
    1. Auto-link existing accounts with matching email.
    2. Set 'patient' role by default for new social signups.
    3. Generate unique username if collision occurs.
    4. Auto-create PatientProfile and save Google profile avatar photo.
    5. Handle role-based redirects post-login.
    """

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # Default new social signups to patient role
        if not user.role:
            user.role = 'patient'

        # Extract name fields
        extra_data = sociallogin.account.extra_data
        first_name = extra_data.get('given_name') or extra_data.get('first_name') or ''
        last_name = extra_data.get('family_name') or extra_data.get('last_name') or ''

        if not first_name or not last_name:
            full_name = extra_data.get('name') or extra_data.get('login') or ''
            if full_name:
                parts = full_name.split(' ', 1)
                first_name = first_name or parts[0]
                last_name = last_name or (parts[1] if len(parts) > 1 else '')

        user.first_name = first_name
        user.last_name = last_name

        # Ensure username is unique
        base_username = user.username or (user.email.split('@')[0] if user.email else 'user')
        base_username = ''.join(c for c in base_username if c.isalnum() or c in '_-')[:120] or 'user'
        candidate_username = base_username

        counter = 1
        while User.objects.filter(username__iexact=candidate_username).exclude(pk=user.pk).exists():
            candidate_username = f"{base_username}_{counter}"
            counter += 1

        user.username = candidate_username
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Link social account to an existing user with the same email address
        to prevent duplicate account errors.
        """
        if sociallogin.is_existing:
            return

        email = sociallogin.user.email
        if email:
            try:
                existing_user = User.objects.get(email__iexact=email)
                sociallogin.connect(request, existing_user)
            except User.DoesNotExist:
                pass

    def save_user(self, request, sociallogin, form=None):
        """
        Save custom user object, create PatientProfile, and fetch avatar picture.
        """
        user = super().save_user(request, sociallogin, form)

        if not user.role:
            user.role = 'patient'
            user.save(update_fields=['role'])

        # Create or fetch PatientProfile safely
        profile, created = PatientProfile.objects.get_or_create(user=user)

        # Retrieve Google or GitHub profile picture URL
        extra_data = sociallogin.account.extra_data
        avatar_url = extra_data.get('picture') or extra_data.get('avatar_url')

        if avatar_url and not profile.photo:
            try:
                response = requests.get(avatar_url, timeout=8)
                if response.status_code == 200:
                    file_name = f"social_avatar_{user.id}.jpg"
                    profile.photo.save(file_name, ContentFile(response.content), save=True)
            except Exception as e:
                print(f"[SOCIAL ADAPTER] Failed to fetch avatar: {e}")

        return user

    def get_login_redirect_url(self, request):
        """
        Role-based redirect post-login:
        - Admin -> /admin-dashboard/
        - Doctor -> /doctor/dashboard/
        - Patient -> /patient/dashboard/
        - Fallback -> /
        """
        user = request.user
        if not user.is_authenticated:
            return '/'

        if user.is_superuser or user.is_staff:
            return reverse('appointment:admin-dashboard')
        elif getattr(user, 'role', '') == 'doctor':
            return reverse('appointment:doctor-dashboard')
        elif getattr(user, 'role', '') == 'patient':
            return reverse('appointment:patient-dashboard')
        return '/'

    def get_connect_redirect_url(self, request, socialaccount):
        return self.get_login_redirect_url(request)
