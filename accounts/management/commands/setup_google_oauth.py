import os
from django.core.management.base import BaseCommand
from django.db import transaction, DatabaseError
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = "Production-ready automated setup for Google OAuth and Site domain configuration."

    def handle(self, *args, **options):
        self.stdout.write("==================================================")
        self.stdout.write("Creating Site...")

        # 1. Read and validate environment variables
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
        secret_key = (
            os.environ.get('GOOGLE_SECRET_KEY', '') or os.environ.get('GOOGLE_CLIENT_SECRET', '')
        ).strip()
        site_domain = os.environ.get('SITE_DOMAIN', 'docmed-fx0m.onrender.com').strip()
        site_name = os.environ.get('SITE_NAME', 'DocMed').strip()

        missing_vars = []
        if not client_id:
            missing_vars.append("GOOGLE_CLIENT_ID")
        if not secret_key:
            missing_vars.append("GOOGLE_SECRET_KEY")

        if missing_vars:
            self.stderr.write(self.style.ERROR("[ERROR] Missing required environment variables:"))
            for var in missing_vars:
                self.stderr.write(self.style.ERROR(f" - {var}: NOT SET"))
            self.stderr.write(
                self.style.ERROR(
                    "\nPlease set GOOGLE_CLIENT_ID and GOOGLE_SECRET_KEY in your environment or Render dashboard."
                )
            )
            self.stdout.write("==================================================")
            return

        try:
            with transaction.atomic():
                # 2. Create or Update Site (id=1)
                site, created_site = Site.objects.update_or_create(
                    id=1,
                    defaults={
                        'domain': site_domain,
                        'name': site_name,
                    }
                )

                if created_site:
                    self.stdout.write("Site created.")
                else:
                    self.stdout.write("Site updated.")

                # 3. Create or Update Google SocialApp
                self.stdout.write("\nCreating Google SocialApp...")

                existing_apps = list(
                    SocialApp.objects.filter(provider='google') | SocialApp.objects.filter(name='Google OAuth')
                )

                if existing_apps:
                    app = existing_apps[0]
                    app.provider = 'google'
                    app.name = 'Google OAuth'
                    app.client_id = client_id
                    app.secret = secret_key
                    app.save()

                    # Clean up any extra duplicate apps
                    for dup_app in existing_apps[1:]:
                        dup_app.delete()

                    self.stdout.write("Google SocialApp updated.")
                else:
                    app = SocialApp.objects.create(
                        provider='google',
                        name='Google OAuth',
                        client_id=client_id,
                        secret=secret_key
                    )
                    self.stdout.write("Google SocialApp created.")

                # Attach Site(id=1) to Google SocialApp
                if not app.sites.filter(id=site.id).exists():
                    app.sites.add(site)

                self.stdout.write("\nAttaching Site...")
                self.stdout.write(self.style.SUCCESS("\nGoogle OAuth setup completed successfully."))
                self.stdout.write("==================================================")

        except ValidationError as e:
            self.stderr.write(self.style.ERROR(f"[ERROR] Validation error during OAuth setup: {e}"))
        except DatabaseError as e:
            self.stderr.write(self.style.ERROR(f"[ERROR] Database error during OAuth setup: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[ERROR] Unexpected error during OAuth setup: {e}"))
