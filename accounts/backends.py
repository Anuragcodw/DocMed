from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib.auth import get_user_model

class MultiFieldBackend(ModelBackend):
    """
    Custom authentication backend that permits authentication using
    email, username, or phone number.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
            
        if not username:
            return None

        try:
            # Match against username (exact/case-insensitive), email, or phone_number
            user = UserModel.objects.get(
                Q(username__iexact=username) |
                Q(email__iexact=username) |
                Q(phone_number=username)
            )
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            # If multiple accounts match (e.g. phone number duplicates), get the first active one
            user = UserModel.objects.filter(
                Q(username__iexact=username) |
                Q(email__iexact=username) |
                Q(phone_number=username)
            ).first()

        if user and user.check_password(password):
            return user
        return None
