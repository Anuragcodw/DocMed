from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = "Reset or create admin user"

    def handle(self, *args, **kwargs):

        EMAIL = "anuragmaurya834@gmail.com"
        PASSWORD = "DocMed@12345"
        USERNAME = "Anurag Maurya"

        User = get_user_model()

        self.stdout.write("=" * 60)
        self.stdout.write("RESET ADMIN COMMAND STARTED")
        self.stdout.write("=" * 60)

        try:
            with transaction.atomic():

                user = User.objects.filter(email__iexact=EMAIL).first()

                if user:

                    self.stdout.write(f"Existing user found : {EMAIL}")

                    if hasattr(user, "username"):
                        user.username = USERNAME

                    user.is_staff = True
                    user.is_superuser = True
                    user.is_active = True

                    user.set_password(PASSWORD)

                    user.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            "Existing admin updated successfully."
                        )
                    )

                else:

                    self.stdout.write(
                        "No existing user found. Creating new superuser..."
                    )

                    kwargs = {
                        "email": EMAIL,
                        "password": PASSWORD,
                    }

                    if hasattr(User, "USERNAME_FIELD"):
                        if User.USERNAME_FIELD != "email":
                            kwargs["username"] = USERNAME

                    try:
                        User.objects.create_superuser(**kwargs)

                    except TypeError:

                        user = User(
                            email=EMAIL
                        )

                        if hasattr(user, "username"):
                            user.username = USERNAME

                        user.is_staff = True
                        user.is_superuser = True
                        user.is_active = True

                        user.set_password(PASSWORD)

                        user.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            "New superuser created successfully."
                        )
                    )

            self.stdout.write("=" * 60)
            self.stdout.write(
                self.style.SUCCESS(
                    "PASSWORD RESET COMPLETED"
                )
            )
            self.stdout.write("=" * 60)

        except Exception as e:

            self.stderr.write(
                self.style.ERROR(
                    f"ERROR : {e}"
                )
            )