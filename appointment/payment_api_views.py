"""
REST API Views for Razorpay Payment, Payment History, and In-App Notifications.
Provides full compatibility for React frontend and Mobile API consumers.
"""

import logging
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TakeAppointment, Payment, InAppNotification
from .serializers import (
    PaymentSerializer, InAppNotificationSerializer,
    RazorpayCreateOrderRequestSerializer, RazorpayVerifyPaymentRequestSerializer
)
from .emails import send_payment_confirmation_email, send_payment_failed_email
from .notification_service import dispatch_payment_notifications, notify_payment_success

logger = logging.getLogger(__name__)


class RazorpayCreateOrderAPIView(APIView):
    """
    API endpoint for React/Mobile apps to create a Razorpay Order.
    POST payload: {"booking_id": 123}
    Returns Razorpay order ID, amount in paise, currency, and prefill details.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = RazorpayCreateOrderRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking_id = serializer.validated_data['booking_id']
        booking = get_object_or_404(TakeAppointment, pk=booking_id, user=request.user)

        # Check if already paid
        if hasattr(booking, 'payment') and booking.payment.status == 'success':
            return Response({'message': 'This appointment is already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        fee = 500.0
        try:
            fee = float(booking.appointment.user.doctor_profile.consultation_fee)
        except Exception:
            pass

        subtotal = fee
        tax_amount = round(subtotal * 0.18, 2)
        total_amount = round(subtotal + tax_amount, 2)
        amount_paise = int(total_amount * 100)

        try:
            import razorpay
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            order_data = {
                'amount': amount_paise,
                'currency': getattr(settings, 'RAZORPAY_CURRENCY', 'INR'),
                'receipt': f'booking_{booking.id}',
                'notes': {
                    'booking_id': str(booking.id),
                    'patient': booking.user.get_full_name(),
                    'doctor': booking.appointment.full_name,
                }
            }
            razorpay_order = client.order.create(data=order_data)

            payment, _ = Payment.objects.get_or_create(booking=booking)
            payment.gateway = 'razorpay'
            payment.amount = total_amount
            payment.status = 'pending'
            payment.razorpay_order_id = razorpay_order['id']
            payment.save()

            return Response({
                'order_id': razorpay_order['id'],
                'amount': amount_paise,
                'currency': getattr(settings, 'RAZORPAY_CURRENCY', 'INR'),
                'key_id': settings.RAZORPAY_KEY_ID,
                'booking_id': booking.id,
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
                'doctor_name': f"Dr. {booking.appointment.full_name}",
                'hospital_name': booking.appointment.hospital_name,
                'prefill': {
                    'name': booking.full_name,
                    'email': booking.user.email,
                    'contact': booking.phone_number,
                }
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f'[API] Razorpay order creation failed: {exc}', exc_info=True)
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RazorpayVerifyPaymentAPIView(APIView):
    """
    API endpoint for React/Mobile apps to verify Razorpay signature server-side.
    POST payload:
    {
        "booking_id": 123,
        "razorpay_order_id": "order_xxx",
        "razorpay_payment_id": "pay_xxx",
        "razorpay_signature": "sig_xxx"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = RazorpayVerifyPaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking_id = serializer.validated_data['booking_id']
        razorpay_order_id = serializer.validated_data['razorpay_order_id']
        razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
        razorpay_signature = serializer.validated_data['razorpay_signature']

        try:
            import razorpay
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            params = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
            client.utility.verify_payment_signature(params)

            payment = get_object_or_404(Payment, razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'success'
            payment.paid_at = timezone.now()

            try:
                razor_pay_obj = client.payment.fetch(razorpay_payment_id)
                payment.payment_method = razor_pay_obj.get('method', 'razorpay')
            except Exception:
                payment.payment_method = 'razorpay'

            payment.save()

            payment.booking.is_paid = True
            payment.booking.status = 'approved'
            payment.booking.save(update_fields=['is_paid', 'status'])

            # Create Google Calendar Event & Google Meet Link
            try:
                from .google_calendar_service import create_google_calendar_event
                create_google_calendar_event(payment.booking)
            except Exception as g_err:
                logger.warning(f'[API] Google Calendar event creation warning: {g_err}')

            # Send Email, SMS, In-App Notifications
            try:
                send_payment_confirmation_email(payment)
                dispatch_payment_notifications(payment)
                notify_payment_success(payment)
            except Exception as notif_err:
                logger.warning(f'[API] Notification dispatch warning: {notif_err}')

            return Response({
                'success': True,
                'message': 'Payment verified successfully!',
                'payment_id': payment.id,
                'invoice_number': payment.invoice_number,
                'status': 'success',
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f'[API] Razorpay payment verification failed: {exc}')
            try:
                p = Payment.objects.filter(booking_id=booking_id).first()
                if p and p.status != 'success':
                    p.status = 'failed'
                    p.save()
            except Exception:
                pass
            return Response({'success': False, 'error': 'Invalid payment signature.'}, status=status.HTTP_400_BAD_REQUEST)


class PatientPaymentHistoryAPIView(APIView):
    """API endpoint to fetch payment history for authenticated patient."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        payments = Payment.objects.filter(
            booking__user=request.user
        ).select_related('booking', 'booking__appointment').order_by('-created_at')
        serializer = PaymentSerializer(payments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class InAppNotificationListView(APIView):
    """API endpoint to list in-app notifications for authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        notifications = InAppNotification.objects.filter(user=request.user).order_by('-created_at')[:30]
        unread_count = InAppNotification.objects.filter(user=request.user, is_read=False).count()
        serializer = InAppNotificationSerializer(notifications, many=True)
        return Response({
            'unread_count': unread_count,
            'notifications': serializer.data,
        }, status=status.HTTP_200_OK)


class MarkNotificationReadAPIView(APIView):
    """API endpoint to mark a specific in-app notification as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        notification = get_object_or_404(InAppNotification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'success': True, 'id': notification.id}, status=status.HTTP_200_OK)


from accounts.models import FCMDeviceToken


class SaveFCMTokenAPIView(APIView):
    """
    API endpoint to register/save an FCM token for the authenticated user.
    Supports single user having multiple active device tokens (FCMDeviceToken model)
    while maintaining user.fcm_token for backward compatibility.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        fcm_token = request.data.get('fcm_token') or request.data.get('token')
        device_info = request.data.get('device_info') or request.META.get('HTTP_USER_AGENT', 'Web Browser')[:250]

        if not fcm_token or not str(fcm_token).strip():
            return Response({'error': 'fcm_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        fcm_token = str(fcm_token).strip()

        # 1. Update/Create FCMDeviceToken for multiple devices support
        device_obj, created = FCMDeviceToken.objects.get_or_create(
            user=request.user,
            token=fcm_token,
            defaults={
                'device_info': device_info,
                'is_active': True,
            }
        )
        if not created and not device_obj.is_active:
            device_obj.is_active = True
            device_obj.save(update_fields=['is_active'])

        # 2. Update user.fcm_token for backward compatibility
        if request.user.fcm_token != fcm_token:
            request.user.fcm_token = fcm_token
            request.user.save(update_fields=['fcm_token'])

        logger.info(f"[FCM API] Token saved for user {request.user.email} (Device: {device_info})")
        return Response({
            'success': True,
            'message': 'FCM token registered successfully.',
            'device_id': device_obj.id,
        }, status=status.HTTP_200_OK)


class DeactivateFCMTokenAPIView(APIView):
    """
    API endpoint to deactivate an FCM token for the authenticated user (e.g. on logout).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        fcm_token = request.data.get('fcm_token') or request.data.get('token')
        if fcm_token:
            fcm_token = str(fcm_token).strip()
            FCMDeviceToken.objects.filter(user=request.user, token=fcm_token).update(is_active=False)
            if request.user.fcm_token == fcm_token:
                request.user.fcm_token = None
                request.user.save(update_fields=['fcm_token'])
        else:
            FCMDeviceToken.objects.filter(user=request.user).update(is_active=False)
            request.user.fcm_token = None
            request.user.save(update_fields=['fcm_token'])

        return Response({'success': True, 'message': 'FCM token deactivated.'}, status=status.HTTP_200_OK)
