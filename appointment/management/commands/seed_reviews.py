"""
Management command to seed 12 approved patient reviews.

Creates TakeAppointment bookings and approved Review records
so the testimonials slider has content to display.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from accounts.models import User
from appointment.models import Appointment, TakeAppointment, Review


REVIEW_DATA = [
    {
        "patient_name": "Sarah Jenkins",
        "rating": 5,
        "text": "The booking process was incredibly smooth. I found a great cardiologist within minutes. The interface is stunning and professional!",
    },
    {
        "patient_name": "Michael Thompson",
        "rating": 5,
        "text": "Excellent platform. Very fast and responsive. I love the modern design and the doctor profiles are very detailed and helpful.",
    },
    {
        "patient_name": "Fatima Khan",
        "rating": 5,
        "text": "DocMed saved me so much time. No more waiting in queues. I booked a pediatrician for my child in under 5 minutes. Highly recommended!",
    },
    {
        "patient_name": "Rahul Ahmed",
        "rating": 5,
        "text": "Found a specialist in my area within 2 minutes. The booking confirmation was instant and the whole experience was world-class!",
    },
    {
        "patient_name": "Priya Sharma",
        "rating": 4,
        "text": "Very professional platform. The doctor I consulted was knowledgeable and the video consultation feature worked flawlessly. Great experience overall.",
    },
    {
        "patient_name": "Anika Das",
        "rating": 5,
        "text": "I was nervous about my first online consultation, but the process was so seamless that I felt completely at ease. Will definitely use again!",
    },
    {
        "patient_name": "James Wilson",
        "rating": 5,
        "text": "The best healthcare booking platform I have ever used. Clean UI, fast loading, and the doctors are genuinely top-notch professionals.",
    },
    {
        "patient_name": "Nusrat Begum",
        "rating": 4,
        "text": "Booking was quick and hassle-free. I appreciate the detailed doctor profiles with qualifications and reviews. Makes choosing much easier.",
    },
    {
        "patient_name": "David Chen",
        "rating": 5,
        "text": "Outstanding service! Got an appointment with a neurologist the same day. The reminder notifications were a nice touch. Five stars!",
    },
    {
        "patient_name": "Amara Okafor",
        "rating": 5,
        "text": "I have tried many healthcare apps but DocMed is by far the most polished and user-friendly. My entire family now uses it for all our medical needs.",
    },
    {
        "patient_name": "Tanvir Hasan",
        "rating": 4,
        "text": "Great platform with a beautiful interface. The search filters helped me find exactly the right doctor for my condition. Very impressed!",
    },
    {
        "patient_name": "Maria Gonzalez",
        "rating": 5,
        "text": "From searching for a doctor to completing my appointment, everything was perfect. The follow-up care suggestions were incredibly thoughtful.",
    },
]


class Command(BaseCommand):
    help = "Seed 12 approved patient reviews for the testimonials slider"

    def handle(self, *args, **options):
        # Skip if reviews already exist
        if Review.objects.filter(is_approved=True).count() >= 12:
            self.stdout.write(self.style.WARNING(
                "Already have 12+ approved reviews. Skipping seed."
            ))
            return

        # We need at least one appointment slot to attach bookings
        appointment = Appointment.objects.first()
        if not appointment:
            # Create a placeholder appointment
            doctor_user = User.objects.filter(role='doctor').first()
            if not doctor_user:
                doctor_user = User.objects.create_user(
                    email='seed_doctor@docmed.com',
                    password='SeedPass123!',
                    first_name='Seed',
                    last_name='Doctor',
                    role='doctor',
                )
            appointment = Appointment.objects.create(
                user=doctor_user,
                full_name=f"Dr. {doctor_user.first_name} {doctor_user.last_name}",
                location='Dhaka, Bangladesh',
                start_time='09:00',
                end_time='17:00',
                qualification_name='MBBS, MD',
                institute_name='Medical Institute',
                hospital_name='DocMed Hospital',
                department='Cardiology',
            )

        created_count = 0
        for i, data in enumerate(REVIEW_DATA):
            # Check if a review with this text already exists
            if Review.objects.filter(text=data["text"]).exists():
                continue

            # Create a patient user for the booking (use email as identifier)
            slug = data["patient_name"].lower().replace(" ", "_").replace(".", "")
            email = f'{slug}@docmed-seed.com'
            patient_user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': data["patient_name"].split()[0],
                    'last_name': ' '.join(data["patient_name"].split()[1:]),
                    'role': 'patient',
                }
            )
            if not patient_user.has_usable_password():
                patient_user.set_password('SeedPass123!')
                patient_user.save()

            # Create a booking
            booking = TakeAppointment.objects.create(
                user=patient_user,
                appointment=appointment,
                full_name=data["patient_name"],
                message=f"Booking for review seed #{i+1}",
                phone_number=f"+880170000{1000+i}",
                date=timezone.now() - timedelta(days=random.randint(1, 90)),
            )

            # Create the review
            Review.objects.create(
                booking=booking,
                rating=data["rating"],
                text=data["text"],
                is_approved=True,
                created_at=timezone.now() - timedelta(days=random.randint(1, 60)),
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {created_count} approved reviews."
        ))
