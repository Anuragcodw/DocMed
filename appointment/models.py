"""
Appointment models.

Defines the data structures for doctor appointment slots
and patient appointment requests.
"""

from django.db import models
from django.utils import timezone

from accounts.models import User

DEPARTMENT_CHOICES = (
    ('Dentistry', 'Dentistry'),
    ('Cardiology', 'Cardiology'),
    ('ENT Specialists', 'ENT Specialists'),
    ('Astrology', 'Astrology'),
    ('Neuroanatomy', 'Neuroanatomy'),
    ('Blood Screening', 'Blood Screening'),
    ('Eye Care', 'Eye Care'),
    ('Physical Therapy', 'Physical Therapy'),
)


class Appointment(models.Model):
    """
    A time-slot posted by a doctor that patients can book.

    Each appointment is owned by one doctor (``user``) and contains
    information about the doctor's qualifications, location, and
    available hours.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    full_name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='appointments/', null=True, blank=True)
    location = models.CharField(max_length=100)
    start_time = models.CharField(max_length=10)
    end_time = models.CharField(max_length=10)
    qualification_name = models.CharField(max_length=100)
    institute_name = models.CharField(max_length=100)
    hospital_name = models.CharField(max_length=100)
    department = models.CharField(choices=DEPARTMENT_CHOICES, max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Appointment Slot'
        verbose_name_plural = 'Appointment Slots'

    def __str__(self):
        return f'{self.full_name} — {self.department}'


class TakeAppointment(models.Model):
    """
    A booking request from a patient for a specific appointment slot.

    Links a patient (``user``) to a doctor's appointment slot and
    stores the patient's contact details and message.
    """

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
    )

    CANCELLATION_REASON_CHOICES = (
        ('schedule_conflict', 'Schedule Conflict'),
        ('found_another_doctor', 'Found Another Doctor'),
        ('recovered', 'Recovered'),
        ('emergency', 'Emergency'),
        ('financial', 'Financial Reasons'),
        ('other', 'Other'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    full_name = models.CharField(max_length=100)
    message = models.TextField()
    phone_number = models.CharField(max_length=120)
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    doctor_notes = models.TextField(blank=True, null=True)
    cancellation_reason = models.CharField(
        max_length=50,
        choices=CANCELLATION_REASON_CHOICES,
        blank=True
    )
    cancellation_notes = models.TextField(blank=True)

    # Video Consultation
    meeting_url = models.URLField(blank=True, null=True, help_text="Jitsi/Zoom/Meet link for online consultation")
    meeting_provider = models.CharField(
        max_length=20, blank=True, null=True,
        choices=[('jitsi', 'Jitsi Meet'), ('zoom', 'Zoom'), ('meet', 'Google Meet')],
        default='jitsi'
    )
    meeting_status = models.CharField(
        max_length=20,
        choices=[('waiting', 'Waiting Room'), ('active', 'Active Call'), ('ended', 'Ended')],
        default='waiting',
        help_text="Status of the tele-consultation meeting"
    )
    meeting_notes = models.TextField(blank=True, null=True, help_text="Doctor notes logged during meeting")

    # Payment tracking
    is_paid = models.BooleanField(default=False)
    payment_required = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Appointment Booking'
        verbose_name_plural = 'Appointment Bookings'

    def __str__(self):
        return f'{self.full_name} → {self.appointment.full_name}'

    @property
    def patient_name(self):
        return self.full_name


class DoctorProfile(models.Model):
    """
    Rich profile data for doctors.
    Extended with cover image, social links, registration number, about, digital signature.
    """
    VERIFICATION_STATUS_CHOICES = (
        ('pending',   'Pending Verification'),
        ('verified',  'Verified'),
        ('rejected',  'Rejected'),
        ('suspended', 'Suspended'),
    )

    GOVT_ID_TYPE_CHOICES = (
        ('aadhaar', 'Aadhaar Card'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('voter_id', 'Voter ID'),
        ('pan_card', 'PAN Card'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        limit_choices_to={'role': 'doctor'}
    )
    photo = models.ImageField(upload_to='doctor_photos/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='doctor_covers/', null=True, blank=True)
    digital_signature = models.ImageField(upload_to='doctor_signatures/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    qualification = models.CharField(max_length=200, blank=True)
    degree = models.CharField(max_length=150, blank=True)
    specialization = models.CharField(choices=DEPARTMENT_CHOICES, max_length=100, blank=True)
    super_specialization = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=100, blank=True)
    hospital = models.CharField(max_length=200, blank=True)
    previous_hospital = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    full_address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bio = models.TextField(blank=True)
    about = models.TextField(blank=True, help_text="Detailed about section for public profile")
    languages = models.CharField(max_length=200, blank=True, help_text="Comma separated languages")
    license_number = models.CharField(max_length=50, blank=True, unique=False)
    medical_registration_number = models.CharField(max_length=50, blank=True)
    medical_council = models.CharField(max_length=150, blank=True)
    working_days = models.CharField(max_length=200, blank=True, help_text="Comma separated working days, e.g. Monday, Wednesday")
    available_time_slots = models.CharField(max_length=250, blank=True, help_text="Available time slots e.g. 09:00 AM - 05:00 PM")
    awards = models.TextField(blank=True)
    certificates = models.TextField(blank=True)

    # NMC (National Medical Commission) Credentials
    nmc_registration_number = models.CharField(
        max_length=100,
        blank=True,
        unique=False,  # Enforced via clean() / form validation
        help_text='NMC Registration Number (mandatory for verification)'
    )
    state_medical_council = models.CharField(
        max_length=200, blank=True,
        help_text='e.g. Maharashtra Medical Council, Delhi Medical Council'
    )
    medical_council_registration_year = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Year of registration with state medical council'
    )
    govt_photo_id_type = models.CharField(
        max_length=30,
        choices=GOVT_ID_TYPE_CHOICES,
        blank=True,
        help_text='Type of government-issued photo ID uploaded'
    )

    # Verification Document Uploads
    degree_certificate = models.FileField(upload_to='doctor_documents/degree/', null=True, blank=True)
    mbbs_degree_certificate = models.FileField(
        upload_to='doctor_documents/mbbs/', null=True, blank=True,
        help_text='Upload MBBS degree certificate (PDF/JPG/PNG, max 10MB)'
    )
    additional_qualification_certificates = models.FileField(
        upload_to='doctor_documents/additional_qualifications/', null=True, blank=True,
        help_text='Upload MD/MS/DM/MCh or other postgraduate certificates'
    )
    license_document = models.FileField(upload_to='doctor_documents/license/', null=True, blank=True)
    govt_id_document = models.FileField(upload_to='doctor_documents/govt_id/', null=True, blank=True)
    additional_documents = models.FileField(upload_to='doctor_documents/additional/', null=True, blank=True)
    selfie_photo = models.ImageField(
        upload_to='doctor_documents/selfie/', null=True, blank=True,
        help_text='Recent selfie/profile photo for identity verification'
    )

    # Verification Audit Trail
    verification_remarks = models.TextField(
        blank=True,
        help_text='Admin remarks on the verification decision (visible to doctor)'
    )
    verified_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_doctors',
        help_text='Admin/Staff who approved or rejected this doctor'
    )
    verification_date = models.DateTimeField(
        null=True, blank=True,
        help_text='Date and time when verification decision was made'
    )
    verification_method = models.CharField(
        max_length=50, blank=True, default='manual',
        help_text='Verification method: manual, nmc_api, digilocker, qr_code'
    )

    # Social Links
    social_facebook = models.URLField(blank=True)
    social_twitter = models.URLField(blank=True)
    social_linkedin = models.URLField(blank=True)
    social_instagram = models.URLField(blank=True)
    social_website = models.URLField(blank=True)

    # Stats
    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    patients_treated = models.PositiveIntegerField(default=0)

    # Status & Availability
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    is_available_today = models.BooleanField(default=True)
    is_online = models.BooleanField(default=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    appointment_duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")

    # Modes
    online_consultation = models.BooleanField(default=True)
    offline_consultation = models.BooleanField(default=True)
    emergency = models.BooleanField(default=False)
    emergency_consultation = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Doctor Profile'
        verbose_name_plural = 'Doctor Profiles'

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} ({self.specialization})"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    @property
    def initials(self):
        fn = self.user.first_name[:1].upper() if self.user.first_name else ''
        ln = self.user.last_name[:1].upper() if self.user.last_name else ''
        return fn + ln or 'DR'

    @property
    def languages_list(self):
        """Return languages as a list."""
        if self.languages:
            return [l.strip() for l in self.languages.split(',') if l.strip()]
        return []

    @property
    def is_available_now(self):
        if not self.is_available_today or not self.is_online:
            return False
        if self.opening_time and self.closing_time:
            now_time = timezone.localtime().time()
            if self.opening_time <= self.closing_time:
                return self.opening_time <= now_time <= self.closing_time
            else:  # Crosses midnight
                return now_time >= self.opening_time or now_time <= self.closing_time
        return True


# ============================================================================
# Doctor Extended Models (Qualifications, Experience, Clinics, Fees, Docs, Slots)
# ============================================================================

class DoctorQualification(models.Model):
    """
    Multiple qualifications per doctor (MBBS, MD, MS, DM, DNB etc.)
    """
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='qualifications'
    )
    degree = models.CharField(max_length=50, help_text="e.g. MBBS, MD, MS")
    institute = models.CharField(max_length=200, help_text="Institution name")
    year = models.PositiveIntegerField(null=True, blank=True, help_text="Year of completion")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-year']
        verbose_name = 'Doctor Qualification'

    def __str__(self):
        return f"{self.degree} — {self.institute}"


class DoctorExperience(models.Model):
    """
    Multiple work experiences per doctor (timeline UI).
    """
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='experiences'
    )
    hospital_name = models.CharField(max_length=200)
    designation = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False, help_text="Currently working here")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Doctor Experience'

    def __str__(self):
        return f"{self.designation} at {self.hospital_name}"


class DoctorClinic(models.Model):
    """
    Doctor can manage multiple clinics/hospitals/online consultation entries.
    """
    CLINIC_TYPE_CHOICES = (
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('online', 'Online Consultation'),
    )
    DAYS_CHOICES = [
        ('Mon', 'Monday'), ('Tue', 'Tuesday'), ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'), ('Fri', 'Friday'), ('Sat', 'Saturday'), ('Sun', 'Sunday'),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='clinics'
    )
    name = models.CharField(max_length=200)
    clinic_type = models.CharField(max_length=20, choices=CLINIC_TYPE_CHOICES, default='clinic')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    working_days = models.CharField(max_length=100, blank=True, help_text="Comma-separated day codes: Mon,Wed,Fri")
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Doctor Clinic'
        ordering = ['-is_primary']

    def __str__(self):
        return f"{self.name} ({self.clinic_type})"


class DoctorFeeStructure(models.Model):
    """
    Detailed consultation fee breakdown per doctor.
    """
    CURRENCY_CHOICES = (
        ('INR', '₹ Indian Rupee'),
        ('USD', '$ US Dollar'),
        ('EUR', '€ Euro'),
        ('GBP', '£ British Pound'),
        ('AED', 'د.إ UAE Dirham'),
    )

    doctor = models.OneToOneField(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='fee_structure'
    )
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='INR')
    clinic_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    video_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    emergency_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    followup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_percent = models.PositiveIntegerField(default=0, help_text="Discount percentage (0-100)")
    free_followup_days = models.PositiveIntegerField(default=0, help_text="Free follow-up within N days")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Doctor Fee Structure'

    def __str__(self):
        return f"Fees for Dr. {self.doctor.user.get_full_name()}"

    @property
    def discounted_clinic_fee(self):
        if self.discount_percent:
            return self.clinic_fee * (1 - self.discount_percent / 100)
        return self.clinic_fee


class DoctorDocument(models.Model):
    """
    Doctor uploads verification documents (license, degree, govt ID).
    """
    DOC_TYPE_CHOICES = (
        ('license', 'Medical License'),
        ('degree', 'Degree Certificate'),
        ('govt_id', 'Government ID'),
        ('other', 'Other'),
    )

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='doctor_documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    admin_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Doctor Document'

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.title}"


class DoctorVacation(models.Model):
    """
    Doctor-managed date blocks (holiday, emergency leave, etc.).
    """
    LEAVE_TYPE_CHOICES = (
        ('holiday', 'Holiday'),
        ('emergency', 'Emergency Leave'),
        ('conference', 'Conference / Training'),
        ('personal', 'Personal Leave'),
        ('recurring', 'Recurring Leave'),
    )

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='vacations'
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, default='holiday')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    is_recurring_weekly = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_date']
        verbose_name = 'Doctor Vacation'

    def __str__(self):
        return f"{self.get_leave_type_display()} ({self.start_date} – {self.end_date})"

    def is_active_today(self):
        today = timezone.localdate()
        return self.start_date <= today <= self.end_date


class DoctorSlot(models.Model):
    """
    Calendar-based recurring time slot created by a doctor.
    Each slot can have a capacity and be automatically disabled when full.
    """
    SESSION_CHOICES = (
        ('morning', 'Morning (6 AM – 12 PM)'),
        ('afternoon', 'Afternoon (12 PM – 5 PM)'),
        ('evening', 'Evening (5 PM – 9 PM)'),
        ('night', 'Night (9 PM – 12 AM)'),
    )
    WEEKDAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='slots'
    )
    session = models.CharField(max_length=20, choices=SESSION_CHOICES, default='morning')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, help_text="Day of week (0=Monday)")
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=1, help_text="Max patients per slot")
    is_active = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False, help_text="Video consultation slot")
    effective_from = models.DateField(default=timezone.now)
    effective_until = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['weekday', 'start_time']
        verbose_name = 'Doctor Slot'

    def __str__(self):
        return f"Dr. {self.doctor.full_name} — {self.get_weekday_display()} {self.start_time}"

    def booked_count_on(self, date):
        """Return number of active bookings on a specific date for this slot."""
        return self.slot_bookings.filter(
            booking_date=date,
            status__in=['pending', 'approved', 'rescheduled']
        ).count()

    def is_available_on(self, date):
        """Check if slot has capacity on a specific date and no vacation blocking."""
        if not self.is_active:
            return False
        # Check if date is within effective range
        if date < self.effective_from:
            return False
        if self.effective_until and date > self.effective_until:
            return False
        # Check vacation blocks
        vacations = self.doctor.vacations.all()
        for v in vacations:
            if v.start_date <= date <= v.end_date:
                return False
        return self.booked_count_on(date) < self.capacity


class DoctorSlotBooking(models.Model):
    """
    Links a TakeAppointment booking to a specific DoctorSlot date instance.
    Provides live slot locking and double-booking prevention.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('rescheduled', 'Rescheduled'),
    )

    slot = models.ForeignKey(
        DoctorSlot,
        on_delete=models.CASCADE,
        related_name='slot_bookings'
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='slot_bookings'
    )
    booking_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    # Link back to old-style TakeAppointment if used via wizard
    take_appointment = models.OneToOneField(
        'TakeAppointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='slot_booking'
    )

    class Meta:
        unique_together = [('slot', 'patient', 'booking_date')]
        ordering = ['-booking_date']
        verbose_name = 'Slot Booking'

    def __str__(self):
        return f"{self.patient.get_full_name()} → {self.slot} on {self.booking_date}"


class PatientProfile(models.Model):
    """
    Rich profile data for patients.
    Extended with gender, cover_image, lifestyle fields.
    """
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not', 'Prefer Not to Say'),
    )
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('unknown', 'Unknown'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        limit_choices_to={'role': 'patient'}
    )
    photo = models.ImageField(upload_to='patient_photos/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='patient_covers/', null=True, blank=True)
    gender = models.CharField(max_length=15, choices=GENDER_CHOICES, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    preferred_specialization = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, blank=True)
    height = models.CharField(max_length=10, blank=True, help_text="e.g. 175 cm or 5'9\"")
    weight = models.CharField(max_length=10, blank=True, help_text="e.g. 70 kg")
    medical_history = models.TextField(blank=True)
    past_diseases = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    chronic_diseases = models.TextField(blank=True)
    surgeries = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    insurance_details = models.TextField(blank=True)
    preferred_language = models.CharField(max_length=50, blank=True)
    # Lifestyle
    smoking = models.CharField(max_length=20, blank=True, choices=[
        ('never', 'Never'), ('occasional', 'Occasional'), ('regular', 'Regular'), ('ex_smoker', 'Ex-Smoker')
    ])
    alcohol = models.CharField(max_length=20, blank=True, choices=[
        ('never', 'Never'), ('occasional', 'Occasional'), ('regular', 'Regular'), ('quit', 'Quit')
    ])
    exercise = models.CharField(max_length=20, blank=True, choices=[
        ('none', 'Sedentary'), ('light', 'Light (1-2x/week)'), ('moderate', 'Moderate (3-4x/week)'), ('active', 'Very Active (5+/week)')
    ])

    class Meta:
        verbose_name = 'Patient Profile'
        verbose_name_plural = 'Patient Profiles'

    def __str__(self):
        return f"Patient: {self.user.first_name} {self.user.last_name}"

    @property
    def initials(self):
        fn = self.user.first_name[:1].upper() if self.user.first_name else ''
        ln = self.user.last_name[:1].upper() if self.user.last_name else ''
        return fn + ln or 'PT'

    @property
    def calculated_age(self):
        """Auto-calculate age from date of birth."""
        if self.date_of_birth:
            today = timezone.localdate()
            born = self.date_of_birth
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return self.age


# ============================================================================
# Patient Extended Models (Emergency Contacts, Insurance)
# ============================================================================

class PatientEmergencyContact(models.Model):
    """
    Emergency contacts for a patient (primary and secondary).
    """
    RELATION_CHOICES = (
        ('spouse', 'Spouse'), ('parent', 'Parent'), ('sibling', 'Sibling'),
        ('child', 'Child'), ('friend', 'Friend'), ('guardian', 'Guardian'), ('other', 'Other'),
    )

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    name = models.CharField(max_length=100)
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary']
        verbose_name = 'Emergency Contact'

    def __str__(self):
        return f"{self.name} ({self.get_relation_display()}) — {self.phone}"


class PatientInsurance(models.Model):
    """
    Patient insurance details with card upload and verification.
    """
    VERIFICATION_STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='insurance_policies'
    )
    company_name = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    insurance_card = models.FileField(upload_to='patient_insurance/%Y/%m/', null=True, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Patient Insurance'

    def __str__(self):
        return f"{self.company_name} — {self.policy_number}"

    def is_expired(self):
        if self.expiry_date:
            return timezone.localdate() > self.expiry_date
        return False


class Review(models.Model):
    """
    Patient review for a completed appointment booking.

    Links to a TakeAppointment (booking) so we can derive
    the patient, doctor, department, location, and date.
    """

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    booking = models.OneToOneField(
        TakeAppointment,
        on_delete=models.CASCADE,
        related_name='review',
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        default=5,
    )
    text = models.TextField(
        help_text="Patient's review text",
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Only approved reviews appear on the Home Page",
    )
    helpful_users = models.ManyToManyField(
        User,
        related_name='helpful_reviews',
        blank=True,
        help_text="Users who found this review helpful"
    )
    doctor_reply = models.TextField(
        blank=True,
        null=True,
        help_text="Doctor's reply/response to the patient review"
    )
    doctor_reply_at = models.DateTimeField(
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Patient Review'
        verbose_name_plural = 'Patient Reviews'

    def __str__(self):
        return f"Review by {self.booking.full_name} — {self.rating}★"

    @property
    def patient_name(self):
        return self.booking.full_name

    @property
    def patient_user(self):
        return self.booking.user

    @property
    def doctor_name(self):
        return self.booking.appointment.full_name

    @property
    def department(self):
        return self.booking.appointment.department

    @property
    def location(self):
        return self.booking.appointment.location

    @property
    def appointment_date(self):
        return self.booking.date

    @property
    def stars_html(self):
        """Returns star emoji string based on rating."""
        return '⭐' * self.rating


# ============================================================================
# Payment Model
# ============================================================================

PAYMENT_GATEWAY_CHOICES = (
    ('razorpay', 'Razorpay'),
    ('stripe', 'Stripe'),
    ('upi', 'UPI'),
    ('cash', 'Cash'),
)

PAYMENT_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('success', 'Success'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
)


class Payment(models.Model):
    """
    Tracks payment transactions for appointment bookings.
    Links to TakeAppointment and stores gateway-specific IDs.
    """
    booking = models.OneToOneField(
        TakeAppointment,
        on_delete=models.CASCADE,
        related_name='payment',
    )
    gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAY_CHOICES, default='razorpay')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')

    # Gateway-specific IDs
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    upi_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    # Invoice
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    receipt_url = models.URLField(blank=True, null=True)

    # Refunds
    refund_requested = models.BooleanField(default=False)
    refund_reason = models.TextField(blank=True, null=True)
    refund_status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ),
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"Payment #{self.invoice_number} — {self.gateway} — {self.status}"

    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not set
        if not self.invoice_number:
            import uuid
            self.invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


# ============================================================================
# Prescription Models
# ============================================================================


class Prescription(models.Model):
    """
    Doctor-created prescription for a completed appointment booking.
    Contains advice, lab tests, and linked medicines.
    """
    booking = models.OneToOneField(
        TakeAppointment,
        on_delete=models.CASCADE,
        related_name='prescription',
    )
    symptoms = models.TextField(blank=True, help_text="Patient's symptoms")
    diagnosis = models.TextField(blank=True, help_text="Medical diagnosis")
    diagnosis_notes = models.TextField(blank=True, help_text="Doctor's diagnosis notes")
    advice = models.TextField(blank=True, help_text="General medical advice")
    lab_tests = models.TextField(blank=True, help_text="Recommended lab tests")
    follow_up_date = models.DateField(null=True, blank=True)
    qr_code = models.ImageField(upload_to='prescription_qrs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'

    def __str__(self):
        return f"Prescription for {self.booking.full_name} by Dr. {self.booking.appointment.full_name}"


class PrescriptionItem(models.Model):
    """
    Individual medicine entry within a Prescription.
    """
    FREQUENCY_CHOICES = (
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('thrice_daily', 'Three Times Daily'),
        ('four_times', 'Four Times Daily'),
        ('as_needed', 'As Needed (SOS)'),
        ('weekly', 'Once Weekly'),
        ('custom', 'Custom'),
    )

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items',
    )
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text="e.g. 500mg")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='twice_daily')
    morning = models.BooleanField(default=False, help_text="Take in morning")
    afternoon = models.BooleanField(default=False, help_text="Take in afternoon")
    night = models.BooleanField(default=False, help_text="Take at night")
    before_food = models.BooleanField(default=False, help_text="Take before food")
    number_of_days = models.PositiveIntegerField(default=1, help_text="Number of days to take medicine")
    duration = models.CharField(max_length=100, blank=True, help_text="e.g. 7 days, 2 weeks")
    instructions = models.CharField(max_length=255, blank=True, help_text="e.g. Take after meals")
    notes = models.TextField(blank=True, help_text="Specific notes for this medicine")

    class Meta:
        verbose_name = 'Prescription Item'
        verbose_name_plural = 'Prescription Items'

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage}) — {self.get_frequency_display()}"


# ============================================================================
# Medical Report Model
# ============================================================================

REPORT_TYPE_CHOICES = (
    ('blood_test', 'Blood Test / CBC'),
    ('urine_report', 'Urine Report'),
    ('mri', 'MRI Scan'),
    ('ct_scan', 'CT Scan'),
    ('xray', 'X-Ray'),
    ('ecg', 'ECG / EKG'),
    ('prescription', 'Prescription'),
    ('liver_function', 'Liver Function Test'),
    ('kidney_function', 'Kidney Function Test'),
    ('thyroid', 'Thyroid Panel'),
    ('lipid_profile', 'Lipid Profile'),
    ('other', 'Other Report'),
)

ALLOWED_REPORT_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg']
MAX_REPORT_SIZE_MB = 10


class MedicalReport(models.Model):
    """
    Patient-uploaded medical report file with optional AI-generated analysis.
    Supports PDF, PNG, JPG formats. Size limit enforced in form validation.
    """
    ANALYSIS_STATUS_CHOICES = (
        ('pending', 'Pending Analysis'),
        ('analyzing', 'Analyzing...'),
        ('done', 'Analysis Complete'),
        ('failed', 'Analysis Failed'),
        ('no_text', 'No Text Extracted'),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='medical_reports',
        limit_choices_to={'role': 'patient'},
    )
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, default='other')
    file = models.FileField(upload_to='medical_reports/%Y/%m/', help_text="Accepted: PDF, PNG, JPG, JPEG")
    doctor_name = models.CharField(max_length=200, blank=True)
    hospital_name = models.CharField(max_length=200, blank=True)
    report_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Additional patient notes")

    # AI Analysis Fields
    extracted_text = models.TextField(blank=True, help_text="OCR/PDF-extracted raw text")
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary of findings")
    ai_findings = models.TextField(blank=True, help_text="AI-highlighted abnormal/normal values")
    ai_recommendation = models.TextField(blank=True, help_text="AI suggested next steps")
    analysis_status = models.CharField(
        max_length=20, choices=ANALYSIS_STATUS_CHOICES, default='pending'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Medical Report'
        verbose_name_plural = 'Medical Reports'

    def __str__(self):
        return f"{self.title} — {self.get_report_type_display()} ({self.patient.get_full_name()})"

    @property
    def file_extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower().lstrip('.') if self.file else ''

    @property
    def is_pdf(self):
        return self.file_extension == 'pdf'

    @property
    def is_image(self):
        return self.file_extension in ['png', 'jpg', 'jpeg']


# Signals for auto-creation
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'doctor':
            DoctorProfile.objects.create(user=instance)
        elif instance.role == 'patient':
            PatientProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == 'doctor':
        if not hasattr(instance, 'doctor_profile'):
            DoctorProfile.objects.create(user=instance)
        else:
            instance.doctor_profile.save()
    elif instance.role == 'patient':
        if not hasattr(instance, 'patient_profile'):
            PatientProfile.objects.create(user=instance)
        else:
            instance.patient_profile.save()


class AIChatSession(models.Model):
    """
    A single conversation session for the AI Healthcare Assistant.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chat_sessions', null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'AI Chat Session'
        verbose_name_plural = 'AI Chat Sessions'

    def __str__(self):
        user_str = self.user.email if self.user else "Anonymous"
        return f"Session {self.session_id} - {user_str}"


class AIChatMessage(models.Model):
    """
    An individual message in an AIChatSession.
    """
    SENDER_CHOICES = (
        ('user', 'User'),
        ('ai', 'AI'),
    )
    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'AI Chat Message'
        verbose_name_plural = 'AI Chat Messages'

    def __str__(self):
        return f"{self.sender}: {self.message_text[:30]}..."


class MeetingChatMessage(models.Model):
    booking = models.ForeignKey(
        TakeAppointment,
        on_delete=models.CASCADE,
        related_name='chat_messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    message = models.TextField()
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Meeting Chat Message'
        verbose_name_plural = 'Meeting Chat Messages'

    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.message[:30]}"


class MeetingFile(models.Model):
    booking = models.ForeignKey(
        TakeAppointment,
        on_delete=models.CASCADE,
        related_name='meeting_files'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to='meeting_files/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Meeting File'
        verbose_name_plural = 'Meeting Files'

    def __str__(self):
        return f"{self.file_name} uploaded by {self.uploaded_by.get_full_name()}"


# ============================================================================
# AI & Medical Report Analysis Models
# ============================================================================

class ExtractedText(models.Model):
    """Raw text extracted from reports using OCR engines."""
    report = models.OneToOneField(
        'MedicalReport',
        on_delete=models.CASCADE,
        related_name='extracted_text_rel'
    )
    raw_text = models.TextField()
    confidence = models.FloatField(default=0.0)
    ocr_engine = models.CharField(max_length=50, default='EasyOCR')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Extracted Text'
        verbose_name_plural = 'Extracted Texts'

    def __str__(self):
        return f"OCR for {self.report.title}"


class Prediction(models.Model):
    """Machine Learning pipeline prediction logs."""
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ml_predictions'
    )
    report = models.ForeignKey(
        'MedicalReport',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='predictions'
    )
    prediction_type = models.CharField(
        max_length=100,
        help_text="e.g. Diabetes, Heart Disease, Stroke, Kidney Disease, BP, BMI"
    )
    result = models.CharField(max_length=255)
    probability = models.FloatField(default=0.0)
    risk_score = models.FloatField(default=0.0)
    lifestyle_suggestions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ML Prediction'
        verbose_name_plural = 'ML Predictions'

    def __str__(self):
        return f"{self.prediction_type} prediction: {self.result}"


class Disease(models.Model):
    """Detailed disease profiling extracted or predicted from medical reports."""
    report = models.ForeignKey(
        'MedicalReport',
        on_delete=models.CASCADE,
        related_name='extracted_diseases'
    )
    name = models.CharField(max_length=255)
    severity = models.CharField(
        max_length=50,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ]
    )
    confidence_score = models.FloatField(default=0.0)
    symptoms = models.TextField(blank=True, null=True)
    causes = models.TextField(blank=True, null=True)
    risk_factors = models.TextField(blank=True, null=True)
    recommended_specialist = models.CharField(max_length=100, blank=True, null=True)
    emergency_level = models.CharField(max_length=50, default='Routine')
    lifestyle_advice = models.TextField(blank=True, null=True)
    food_recommendations = models.TextField(blank=True, null=True)
    medicine_category = models.CharField(max_length=255, blank=True, null=True)
    possible_lab_tests = models.TextField(blank=True, null=True)
    emergency_warning = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Extracted Disease'
        verbose_name_plural = 'Extracted Diseases'

    def __str__(self):
        return self.name


class Medicine(models.Model):
    """Medicines extracted from prescription files or AI analyses."""
    report = models.ForeignKey(
        'MedicalReport',
        on_delete=models.CASCADE,
        related_name='extracted_medicines_rel',
        null=True,
        blank=True
    )
    booking = models.ForeignKey(
        TakeAppointment,
        on_delete=models.CASCADE,
        related_name='extracted_medicines',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    why_prescribed = models.TextField(blank=True, null=True)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    timing = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Morning/Afternoon/Night")
    food_instructions = models.CharField(max_length=255, blank=True, null=True, help_text="Before/After food")
    warnings = models.TextField(blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    storage = models.CharField(max_length=255, blank=True, null=True)
    number_of_days = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Extracted Medicine'
        verbose_name_plural = 'Extracted Medicines'

    def __str__(self):
        return self.name


class LabValue(models.Model):
    """Specific lab parameters and status extracted from lab tests."""
    report = models.ForeignKey(
        'MedicalReport',
        on_delete=models.CASCADE,
        related_name='lab_values_rel'
    )
    parameter_name = models.CharField(max_length=100)
    value = models.FloatField()
    unit = models.CharField(max_length=50)
    reference_range = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'Normal'),
            ('abnormal', 'Abnormal'),
            ('critical', 'Critical')
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Extracted Lab Value'
        verbose_name_plural = 'Extracted Lab Values'

    def __str__(self):
        return f"{self.parameter_name}: {self.value} {self.unit} ({self.status})"


class AIAnalysis(models.Model):
    """AI analysis result summary for medical reports."""
    report = models.OneToOneField(
        'MedicalReport',
        on_delete=models.CASCADE,
        related_name='ai_analysis_rel'
    )
    detected_diseases = models.TextField(blank=True, null=True)
    possible_diseases = models.TextField(blank=True, null=True)
    confidence_score = models.FloatField(default=0.0)
    abnormal_values = models.TextField(blank=True, null=True)
    normal_values = models.TextField(blank=True, null=True)
    critical_values = models.TextField(blank=True, null=True)
    possible_causes = models.TextField(blank=True, null=True)
    lifestyle_advice = models.TextField(blank=True, null=True)
    food_advice = models.TextField(blank=True, null=True)
    exercise_advice = models.TextField(blank=True, null=True)
    next_steps = models.TextField(blank=True, null=True)
    recommended_specialist = models.CharField(max_length=100, blank=True, null=True)
    emergency_warning = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'AI Analysis'
        verbose_name_plural = 'AI Analyses'

    def __str__(self):
        return f"AI Analysis for {self.report.title}"


class VoiceSummary(models.Model):
    """Multilingual voice summaries generated for report contents."""
    report = models.ForeignKey(
        'MedicalReport',
        on_delete=models.CASCADE,
        related_name='voice_summaries'
    )
    audio_file = models.FileField(upload_to='voice_summaries/%Y/%m/')
    language = models.CharField(max_length=50, default='English')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Voice Summary'
        verbose_name_plural = 'Voice Summaries'

    def __str__(self):
        return f"{self.language} audio for {self.report.title}"



