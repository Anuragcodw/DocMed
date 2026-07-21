"""
Appointment admin configuration.

Registers Appointment and TakeAppointment with customized admin views.
"""

from django.contrib import admin

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


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'city', 'is_verified', 'is_available_today', 'is_online')
    list_filter = ('is_verified', 'is_available_today', 'is_online', 'specialization', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'hospital', 'city', 'state')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Personal Info', {
            'fields': ('user', 'photo', 'bio')
        }),
        ('Professional Info', {
            'fields': ('qualification', 'specialization', 'experience_years', 'languages')
        }),
        ('Location & Contact', {
            'fields': ('hospital', 'city', 'state', 'country', 'full_address', 'latitude', 'longitude')
        }),
        ('Consultation Details', {
            'fields': ('consultation_fee', 'appointment_duration', 'online_consultation', 'offline_consultation', 'emergency')
        }),
        ('Status & Availability', {
            'fields': ('is_verified', 'is_available_today', 'is_online', 'opening_time', 'closing_time')
        }),
        ('Stats', {
            'fields': ('rating', 'review_count', 'patients_treated')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
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
