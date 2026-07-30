import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = "Reset or create admin user for production. Reads credentials from env vars or uses hardcoded fallbacks."

    def handle(self, *args, **kwargs):
        # Read from environment variables (production) or fallback (local)
        EMAIL = os.environ.get('ADMIN_EMAIL', 'anuragmaurya834@gmail.com')
        PASSWORD = os.environ.get('ADMIN_PASSWORD', 'DocMed@12345')
        USERNAME = os.environ.get('ADMIN_USERNAME', 'Anurag Maurya')

        User = get_user_model()

        self.stdout.write("=" * 60)
        self.stdout.write("RESET ADMIN COMMAND STARTED")
        self.stdout.write(f"Target email: {EMAIL}")
        self.stdout.write("=" * 60)

        try:
            with transaction.atomic():
                user = User.objects.filter(email__iexact=EMAIL).first()

                if user:
                    self.stdout.write(f"Existing user found: {EMAIL}")

                    if hasattr(user, 'username'):
                        user.username = USERNAME

                    user.is_staff = True
                    user.is_superuser = True
                    user.is_active = True

                    # Ensure role is set — PostgreSQL enforces NOT NULL unlike SQLite
                    if not getattr(user, 'role', None):
                        user.role = 'patient'

                    user.set_password(PASSWORD)
                    user.save()

                    self.stdout.write(self.style.SUCCESS("Existing admin updated successfully."))

                else:
                    self.stdout.write("No existing user found. Creating new superuser...")

                    user = User(
                        email=EMAIL,
                        username=USERNAME,
                        is_staff=True,
                        is_superuser=True,
                        is_active=True,
                        # role is required — PostgreSQL enforces this strictly
                        role='patient',
                    )
                    user.set_password(PASSWORD)
                    user.save()

                    self.stdout.write(self.style.SUCCESS("New superuser created successfully."))

            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS("PASSWORD RESET COMPLETED"))
            self.stdout.write(f"Email   : {EMAIL}")
            self.stdout.write(f"Password: {PASSWORD}")
            self.stdout.write("=" * 60)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"ERROR: {e}"))