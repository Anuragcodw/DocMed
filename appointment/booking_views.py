"""
Booking Management Views.
Handles the 5-step booking wizard, review submission, and booking history.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from appointment.decorators import user_is_patient
from appointment.models import (
    Appointment, DoctorProfile, DoctorSlot, DoctorSlotBooking,
    TakeAppointment, Review,
)

LOGIN_URL = reverse_lazy('accounts:login')


# ============================================================================
# 5-Step Booking Wizard
# ============================================================================

class BookingWizardView(LoginRequiredMixin, View):
    """
    5-Step premium booking wizard:
    Step 1 - Choose Doctor
    Step 2 - Choose Date
    Step 3 - Choose Time Slot
    Step 4 - Confirm Details & Payment Method
    Step 5 - Booking Confirmation
    """
    template_name = 'appointment/booking_wizard.html'
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        step = int(request.GET.get('step', 1))
        doctor_id = request.GET.get('doctor_id', '')
        selected_date = request.GET.get('date', '')
        slot_id = request.GET.get('slot_id', '')

        context = {
            'step': step,
            'doctor_id': doctor_id,
            'selected_date': selected_date,
            'slot_id': slot_id,
        }

        if step >= 1 and doctor_id:
            try:
                context['doctor'] = DoctorProfile.objects.select_related('user').get(pk=doctor_id)
            except DoctorProfile.DoesNotExist:
                pass

        if step >= 3 and selected_date and doctor_id:
            try:
                from datetime import date as date_cls
                query_date = date_cls.fromisoformat(selected_date)
                weekday = query_date.weekday()
                slots = DoctorSlot.objects.filter(
                    doctor_id=doctor_id, weekday=weekday, is_active=True
                )
                context['available_slots'] = [s for s in slots if s.is_available_on(query_date)]
            except (ValueError, TypeError):
                context['available_slots'] = []

        if step >= 4 and slot_id:
            try:
                context['selected_slot'] = DoctorSlot.objects.get(pk=slot_id)
            except DoctorSlot.DoesNotExist:
                pass

        # Doctors list for step 1
        if step == 1:
            from appointment.models import DEPARTMENT_CHOICES
            q = request.GET.get('q', '')
            dept = request.GET.get('dept', '')
            doctors = DoctorProfile.objects.select_related('user').filter(is_available_today=True)
            if q:
                from django.db.models import Q
                doctors = doctors.filter(
                    Q(user__first_name__icontains=q) |
                    Q(user__last_name__icontains=q) |
                    Q(specialization__icontains=q)
                )
            if dept:
                doctors = doctors.filter(specialization__iexact=dept)
            context['doctors'] = doctors.order_by('-rating')[:20]
            context['dept_choices'] = DEPARTMENT_CHOICES
            context['q'] = q
            context['dept'] = dept

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Handle final booking submission (Step 4 → Step 5)."""
        doctor_id = request.POST.get('doctor_id')
        slot_id = request.POST.get('slot_id')
        booking_date_str = request.POST.get('booking_date')
        message = request.POST.get('message', '')
        phone = request.POST.get('phone', request.user.phone_number or '')

        try:
            doctor = DoctorProfile.objects.get(pk=doctor_id)
            slot = DoctorSlot.objects.get(pk=slot_id, doctor=doctor)
            from datetime import date as date_cls
            booking_date = date_cls.fromisoformat(booking_date_str)
        except (DoctorProfile.DoesNotExist, DoctorSlot.DoesNotExist, ValueError, TypeError):
            messages.error(request, 'Invalid booking details. Please try again.')
            return redirect('appointment:booking-wizard')

        # Check slot still available
        if not slot.is_available_on(booking_date):
            messages.error(request, 'Sorry! This slot is no longer available. Please choose another.')
            return redirect(
                f"{reverse_lazy('appointment:booking-wizard')}?step=3&doctor_id={doctor_id}&date={booking_date_str}"
            )

        # Check duplicate
        if DoctorSlotBooking.objects.filter(
            slot=slot, patient=request.user, booking_date=booking_date,
            status__in=['pending', 'approved']
        ).exists():
            messages.warning(request, 'You already have a booking for this slot and date.')
            return redirect('appointment:patient-bookings')

        # Create the slot booking
        slot_booking = DoctorSlotBooking.objects.create(
            slot=slot,
            patient=request.user,
            booking_date=booking_date,
            status='pending',
            notes=message,
        )

        # Also create a legacy TakeAppointment if doctor has an Appointment slot
        legacy_appointment = Appointment.objects.filter(user=doctor.user).first()
        if legacy_appointment:
            from datetime import datetime, time
            import pytz
            booking_dt = datetime.combine(
                booking_date,
                slot.start_time,
                tzinfo=timezone.get_current_timezone()
            )
            take = TakeAppointment.objects.create(
                user=request.user,
                appointment=legacy_appointment,
                full_name=request.user.get_full_name(),
                message=message,
                phone_number=phone,
                date=booking_dt,
                status='pending',
            )
            slot_booking.take_appointment = take
            slot_booking.save(update_fields=['take_appointment'])

        messages.success(
            request,
            f'Your appointment with Dr. {doctor.full_name} on {booking_date} has been booked!'
        )
        return redirect('appointment:patient-bookings')


# ============================================================================
# Review Submit
# ============================================================================

class SubmitReviewView(LoginRequiredMixin, View):
    """Allow a patient to submit a review for a completed appointment."""
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(
            TakeAppointment,
            pk=booking_id,
            user=request.user,
            status='completed'
        )

        # Prevent duplicate reviews
        if hasattr(booking, 'review'):
            messages.warning(request, 'You have already submitted a review for this appointment.')
            return redirect('appointment:patient-bookings')

        rating = request.POST.get('rating', 5)
        text = request.POST.get('review_text', '').strip()

        try:
            rating = int(rating)
            if not 1 <= rating <= 5:
                raise ValueError()
        except (ValueError, TypeError):
            rating = 5

        if not text:
            messages.error(request, 'Please write a review before submitting.')
            return redirect('appointment:patient-bookings')

        Review.objects.create(
            booking=booking,
            rating=rating,
            text=text,
            is_approved=False,  # Admin must approve before appearing on homepage
        )
        messages.success(request, 'Thank you! Your review has been submitted and is pending approval.')
        return redirect('appointment:patient-bookings')


# ============================================================================
# Booking Detail View
# ============================================================================

class BookingDetailView(LoginRequiredMixin, View):
    """Full detail view for a single booking."""
    template_name = 'appointment/booking_detail.html'
    login_url = LOGIN_URL

    def get(self, request, pk, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=pk)

        # Security: patient or doctor can view
        is_patient = booking.user == request.user
        is_doctor = booking.appointment.user == request.user
        if not is_patient and not is_doctor and not request.user.is_staff:
            messages.error(request, 'Access denied.')
            return redirect('appointment:home')

        has_review = hasattr(booking, 'review')
        has_prescription = hasattr(booking, 'prescription')
        has_payment = hasattr(booking, 'payment')

        context = {
            'booking': booking,
            'is_patient': is_patient,
            'is_doctor': is_doctor,
            'has_review': has_review,
            'has_prescription': has_prescription,
            'has_payment': has_payment,
        }
        return render(request, self.template_name, context)


# ============================================================================
# Review Management Actions (Like, Reply, Edit, Delete)
# ============================================================================

class LikeReviewView(LoginRequiredMixin, View):
    """Toggle marking a review as helpful."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        if request.user in review.helpful_users.all():
            review.helpful_users.remove(request.user)
            liked = False
        else:
            review.helpful_users.add(request.user)
            liked = True
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': review.helpful_users.count()
        })


class DoctorReplyReviewView(LoginRequiredMixin, View):
    """Allow a doctor to reply/respond to a patient's review."""
    login_url = LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        
        # Verify the logged-in user is the doctor who was reviewed
        if review.booking.appointment.user != request.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            
        reply_text = request.POST.get('reply_text', '').strip()
        if not reply_text:
            return JsonResponse({'success': False, 'error': 'Reply text cannot be empty'}, status=400)
            
        review.doctor_reply = reply_text
        review.doctor_reply_at = timezone.now()
        review.save()
        
        return JsonResponse({
            'success': True,
            'reply': review.doctor_reply,
            'reply_at': review.doctor_reply_at.strftime('%B %d, %Y at %I:%M %p')
        })


class UpdateReviewView(LoginRequiredMixin, View):
    """Allow a patient to edit their existing review."""
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk, booking__user=request.user)
        rating = request.POST.get('rating')
        text = request.POST.get('review_text', '').strip()

        try:
            rating = int(rating)
            if not 1 <= rating <= 5:
                raise ValueError()
            review.rating = rating
        except (ValueError, TypeError):
            pass

        if text:
            review.text = text
            review.is_approved = False  # Re-moderation required
            review.save()
            messages.success(request, 'Your review has been updated and is pending moderation.')
        else:
            messages.error(request, 'Review text cannot be empty.')
            
        return redirect('appointment:patient-bookings')


class DeleteReviewView(LoginRequiredMixin, View):
    """Allow a patient to delete their review."""
    login_url = LOGIN_URL

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk, booking__user=request.user)
        review.delete()
        messages.success(request, 'Your review has been deleted.')
        return redirect('appointment:patient-bookings')

