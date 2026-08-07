"""
Appointment admin configuration.

Registers Appointment and TakeAppointment with customized admin views.
Enhanced DoctorProfileAdmin with NMC verification workflow:
  - Full NMC credential display
  - Bulk Approve / Reject / Suspend / Mark Under Review actions
  - Secure document preview links (all 7 document types)
  - Verification audit trail (verified_by, verification_date, remarks)
"""

from django.contrib import admin
from django.utils import timezone

from .models import Appointment, DoctorProfile, PatientProfile, Review, TakeAppointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin view for doctor-posted appointment slots."""

    list_display = ('full_name', 'department', 'hospital_name', 'location', 'created_at')
    list_filter = ('department', 'created_at')
    search_fields = ('full_name', 'hospital_name', 'location', 'department')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(TakeAppointment)
class TakeAppointmentAdmin(admin.ModelAdmin):
    """Admin view for patient appointment requests."""

    list_display = ('full_name', 'appointment', 'phone_number', 'date')
    list_filter = ('date',)
    search_fields = ('full_name', 'phone_number')
    ordering = ('-date',)
    date_hierarchy = 'date'
    readonly_fields = ('date',)


from django.utils.html import format_html
from accounts.verification_service import DoctorVerificationService


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    """
    Doctor Verification Admin Module — NMC & Automated Approval Workflow Edition.

    Allows administrators to:
      • View all NMC credentials submitted by doctors
      • Inspect auto-generated Doctor ID, Registration ID, and NMC Certificate Number
      • Preview all uploaded verification documents inline
      • Bulk Approve (Auto-generates IDs & sends verification email)
      • Bulk Reject / Suspend (Sends rejection notice with admin remarks)
      • Record verification remarks, verified_by, and verification_date
    """

    list_display = (
        'doctor_id_code',
        'user',
        'nmc_certificate_number',
        'nmc_registration_number',
        'specialization',
        'state_medical_council',
        'verification_status',
        'is_verified',
        'created_at',
    )
    list_filter = (
        'verification_status',
        'is_verified',
        'specialization',
        'verification_method',
        'govt_photo_id_type',
        'created_at',
    )
    search_fields = (
        'doctor_id_code',
        'nmc_certificate_number',
        'registration_id',
        'user__first_name',
        'user__last_name',
        'user__email',
        'nmc_registration_number',
        'medical_registration_number',
        'license_number',
        'state_medical_council',
        'hospital',
        'city',
    )
    readonly_fields = (
        'doctor_id_code',
        'registration_id',
        'nmc_certificate_number',
        'nmc_registration_number',
        'state_medical_council',
        'medical_council_registration_year',
        'created_at',
        'updated_at',
        # Secure document preview links
        'degree_certificate_link',
        'mbbs_certificate_link',
        'additional_qualifications_link',
        'license_document_link',
        'govt_id_document_link',
        'additional_documents_link',
        'selfie_photo_link',
    )
    actions = [
        'approve_doctors',
        'reject_doctors',
        'suspend_doctors',
    ]

    # ------------------------------------------------------------------ #
    # Bulk Actions                                                        #
    # ------------------------------------------------------------------ #

    @admin.action(description='✅ Approve selected Doctor Registrations (Auto-Generate IDs & Send Email)')
    def approve_doctors(self, request, queryset):
        count = 0
        for profile in queryset:
            DoctorVerificationService.approve_doctor(profile, admin_user=request.user)
            count += 1
        self.message_user(request, f"✅ Successfully verified {count} doctor account(s). Doctor IDs & NMC Certificate Numbers generated, and confirmation emails sent.")

    @admin.action(description='❌ Reject selected Doctor Registrations (Send Rejection Email)')
    def reject_doctors(self, request, queryset):
        count = 0
        for profile in queryset:
            DoctorVerificationService.reject_doctor(profile, admin_user=request.user, remarks=profile.verification_remarks)
            count += 1
        self.message_user(request, f"❌ Rejected {count} doctor account(s). Rejection notifications sent to registered emails.")

    @admin.action(description='⚠️ Suspend selected Doctor Registrations')
    def suspend_doctors(self, request, queryset):
        count = queryset.update(
            verification_status='suspended',
            is_verified=False,
            verified_by=request.user,
            verification_date=timezone.now(),
        )
        self.message_user(request, f"⚠️ Suspended {count} doctor account(s).")

    def save_model(self, request, obj, form, change):
        """
        Handle single DoctorProfile save in Admin.
        Triggers ID generation and email notification when status changes to 'verified' or 'rejected'.
        """
        if change:
            orig = DoctorProfile.objects.filter(pk=obj.pk).first()
            if orig and orig.verification_status != obj.verification_status:
                if obj.verification_status == 'verified':
                    DoctorVerificationService.approve_doctor(obj, admin_user=request.user, remarks=obj.verification_remarks)
                    return
                elif obj.verification_status == 'rejected':
                    DoctorVerificationService.reject_doctor(obj, admin_user=request.user, remarks=obj.verification_remarks)
                    return

        # If IDs aren't set but status is verified, generate them
        if obj.verification_status == 'verified' and not obj.doctor_id_code:
            obj.generate_approval_ids()
            obj.is_verified = True
            if not obj.verification_date:
                obj.verification_date = timezone.now()

        super().save_model(request, obj, form, change)


    # ------------------------------------------------------------------ #
    # Document Preview Links                                              #
    # ------------------------------------------------------------------ #

    def _doc_link(self, file_field, label, icon='📄'):
        if file_field and file_field.name:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener" '
                    'style="font-weight:bold;color:#4f46e5;">'
                    '{} View {}</a>',
                    file_field.url, icon, label,
                )
            except ValueError:
                pass
        return format_html('<span style="color:#9ca3af;">No file uploaded</span>')

    def degree_certificate_link(self, obj):
        return self._doc_link(obj.degree_certificate, 'Degree Certificate', '🎓')
    degree_certificate_link.short_description = '📄 Degree Certificate'

    def mbbs_certificate_link(self, obj):
        return self._doc_link(obj.mbbs_degree_certificate, 'MBBS Degree Certificate', '🎓')
    mbbs_certificate_link.short_description = '📄 MBBS Certificate'

    def additional_qualifications_link(self, obj):
        return self._doc_link(obj.additional_qualification_certificates, 'Additional Qualifications (MD/MS/DM)', '📚')
    additional_qualifications_link.short_description = '📄 Additional Qualifications'

    def license_document_link(self, obj):
        return self._doc_link(obj.license_document, 'Medical License Document', '⚕️')
    license_document_link.short_description = '📄 Medical License'

    def govt_id_document_link(self, obj):
        label = f'Government ID ({obj.get_govt_photo_id_type_display() or "Unknown Type"})'
        return self._doc_link(obj.govt_id_document, label, '🪪')
    govt_id_document_link.short_description = '📄 Government ID'

    def additional_documents_link(self, obj):
        return self._doc_link(obj.additional_documents, 'Additional Documents', '📎')
    additional_documents_link.short_description = '📄 Additional Documents'

    def selfie_photo_link(self, obj):
        return self._doc_link(obj.selfie_photo, 'Selfie / Profile Photo', '🤳')
    selfie_photo_link.short_description = '📄 Selfie / Profile Photo'

    # ------------------------------------------------------------------ #
    # Admin Fieldsets                                                     #
    # ------------------------------------------------------------------ #

    fieldsets = (
        ('👤 Personal Information', {
            'fields': ('user', 'photo', 'date_of_birth', 'bio'),
        }),

        ('🏥 NMC Registration & Medical Council Credentials', {
            'fields': (
                'nmc_registration_number',
                'state_medical_council',
                'medical_council_registration_year',
                'medical_registration_number',
                'license_number',
                'medical_council',
                'qualification',
                'degree',
                'specialization',
                'super_specialization',
                'department',
                'experience_years',
                'languages',
            ),
            'description': (
                '⚠️ NMC Registration Number is mandatory for verification. '
                'Verify against the NMC public registry at nmc.org.in before approving.'
            ),
        }),

        ('📂 Uploaded Verification Documents', {
            'fields': (
                # Selfie
                'selfie_photo_link',
                # Degrees
                'degree_certificate',
                'degree_certificate_link',
                'mbbs_degree_certificate',
                'mbbs_certificate_link',
                'additional_qualification_certificates',
                'additional_qualifications_link',
                # License & Govt ID
                'license_document',
                'license_document_link',
                'govt_photo_id_type',
                'govt_id_document',
                'govt_id_document_link',
                # Other
                'additional_documents',
                'additional_documents_link',
            ),
        }),

        ('📍 Location & Hospital', {
            'fields': (
                'hospital',
                'previous_hospital',
                'city',
                'state',
                'country',
                'full_address',
                'latitude',
                'longitude',
            ),
        }),

        ('🗓️ Consultation Details & Hours', {
            'fields': (
                'consultation_fee',
                'appointment_duration',
                'working_days',
                'available_time_slots',
                'online_consultation',
                'offline_consultation',
                'emergency',
                'emergency_consultation',
            ),
        }),

        ('✅ Verification & Approval Status', {
            'fields': (
                'verification_status',
                'is_verified',
                'verification_method',
                'verification_remarks',
                'verified_by',
                'verification_date',
                'is_available_today',
                'is_online',
            ),
            'description': (
                '📝 Set Verification Remarks so the doctor can see the reason for approval/rejection '
                'on their verification status page.'
            ),
        }),

        ('⏱️ Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'state', 'preferred_specialization')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'city', 'state')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Admin view for patient reviews / testimonials."""

    list_display = ('booking', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('booking__full_name', 'text')
    ordering = ('-created_at',)
    actions = ['approve_reviews', 'reject_reviews']

    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='Reject selected reviews')
    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
