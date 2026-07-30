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

        try:
            # Match against email, username (case-insensitive), or phone_number
            user = UserModel.objects.get(
                Q(email__iexact=username) |
                Q(username__iexact=username) |
                Q(phone_number=username)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce timing attack surface
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # If multiple accounts match, prefer the active one
            user = UserModel.objects.filter(
                Q(email__iexact=username) |
                Q(username__iexact=username) |
                Q(phone_number=username)
            ).filter(is_active=True).first()
            if not user:
                return None

        # check_password + user_can_authenticate (checks is_active) — same as ModelBackend
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
