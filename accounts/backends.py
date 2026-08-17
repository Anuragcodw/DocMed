from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib.auth import get_user_model


class MultiFieldBackend(ModelBackend):
    """
    Custom authentication backend that permits authentication using
    email, username, or phone number.

    Inherits user_can_authenticate() from ModelBackend which checks is_active.
    This ensures Django admin confirm_login_allowed() works correctly.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        # Django admin form always passes the value as 'username' kwarg.
        # When called directly with email= kwarg (e.g. in shell), fall back to USERNAME_FIELD.
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if not username or not password:
            return None

        clean_credential = username.strip()
        matching_users = UserModel.objects.filter(
            Q(email__iexact=clean_credential) |
            Q(username__iexact=clean_credential) |
            Q(phone_number=clean_credential)
        ).filter(is_active=True)

        if not matching_users.exists():
            # Run the default password hasher once to reduce timing attack surface
            UserModel().set_password(password)
            return None

        for user in matching_users:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None
