from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = "Temporary administrative recovery command to reset or create the primary superuser."

    def handle(self, *args, **options):
        email = "anuragmaurya834@gmail.com"
        password = "DocMed@12345"
        desired_username = "Anurag Maurya"

        try:
            User = get_user_model()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"User model initialization error: {e}"))
            return

        try:
            with transaction.atomic():
                # Check if user with target email already exists
                user = User.objects.filter(email__iexact=email).first()

                if user:
                    # Update existing user credentials and admin privileges
                    user.set_password(password)
                    user.is_staff = True
                    user.is_superuser = True
                    user.is_active = True
                    if not user.username:
                        # Ensure username field is populated if empty
                        user.username = desired_username
                    user.save()
                    self.stdout.write(self.style.SUCCESS("Existing admin updated successfully."))
                else:
                    # Handle possible username collision before creation
                    existing_username_user = User.objects.filter(username=desired_username).first()
                    username_to_use = desired_username
                    if existing_username_user:
                        username_to_use = "anuragmaurya834"

                    # Create new superuser
                    if hasattr(User.objects, 'create_superuser'):
                        User.objects.create_superuser(
                            email=email,
                            username=username_to_use,
                            password=password,
                            is_staff=True,
                            is_superuser=True,
                            is_active=True
                        )
                    else:
                        user = User(
                            email=email,
                            username=username_to_use,
                            is_staff=True,
                            is_superuser=True,
                            is_active=True
                        )
                        user.set_password(password)
                        user.save()

                    self.stdout.write(self.style.SUCCESS("New superuser created successfully."))

        except IntegrityError as e:
            self.stderr.write(self.style.ERROR(f"Database integrity error during admin reset: {e}"))
        except ValidationError as e:
            self.stderr.write(self.style.ERROR(f"Validation error during admin reset: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Unexpected error during admin reset: {e}"))
