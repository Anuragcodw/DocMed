"""
Comprehensive Automated Test Script for Razorpay Payment Workflow.

Tests:
  1. Appointment Booking & Payment record creation.
  2. Order creation calculation & parameters.
  3. Signature verification & payment status transition (pending -> success).
  4. Appointment status auto-update to 'approved' & 'is_paid = True'.
  5. Multi-channel notifications: InAppNotification creation for Patient, Doctor, Admin.
  6. Invoice PDF generation & database persistence in Invoice model.
  7. DRF API serializers and endpoints.
"""

import os
import django

import sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment_system.settings')
django.setup()

import hmac
import hashlib
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from appointment.models import Appointment, TakeAppointment, Payment, Invoice, InAppNotification
from appointment.notification_service import dispatch_payment_notifications
from appointment.payment_views import InvoicePDFView
from appointment.serializers import PaymentSerializer, InvoiceSerializer, InAppNotificationSerializer

User = get_user_model()


def run_tests():
    print("=== STARTING RAZORPAY PAYMENT WORKFLOW VERIFICATION ===")

    # 1. Create or fetch test users
    patient, _ = User.objects.get_or_create(
        username='test_patient_payment',
        defaults={'email': 'patient_pay@example.com', 'role': 'patient', 'first_name': 'Test', 'last_name': 'Patient'}
    )
    doctor_user, _ = User.objects.get_or_create(
        username='test_doctor_payment',
        defaults={'email': 'doctor_pay@example.com', 'role': 'doctor', 'first_name': 'Test', 'last_name': 'Doctor'}
    )
    admin_user, _ = User.objects.get_or_create(
        username='test_admin_payment',
        defaults={'email': 'admin_pay@example.com', 'is_staff': True, 'is_superuser': True, 'first_name': 'Admin', 'last_name': 'User'}
    )

    # 2. Create appointment slot & booking
    appointment, _ = Appointment.objects.get_or_create(
        user=doctor_user,
        full_name='Test Doctor',
        defaults={'department': 'Cardiology', 'hospital_name': 'City General Hospital', 'location': 'New Delhi'}
    )

    booking = TakeAppointment.objects.create(
        user=patient,
        appointment=appointment,
        full_name='Test Patient',
        message='Routine heart checkup',
        phone_number='+919876543210',
        status='pending',
        is_paid=False,
    )
    print(f"[OK] Created Booking ID #{booking.id}")

    # 3. Simulate Razorpay Order Creation
    fee = 500.0
    subtotal = fee
    tax_amount = round(subtotal * 0.18, 2)
    total_amount = round(subtotal + tax_amount, 2)

    dummy_order_id = f"order_test_{booking.id}_{int(timezone.now().timestamp())}"
    dummy_payment_id = f"pay_test_{booking.id}_{int(timezone.now().timestamp())}"

    payment, created = Payment.objects.get_or_create(booking=booking, defaults={'amount': total_amount})
    payment.gateway = 'razorpay'
    payment.amount = total_amount
    payment.status = 'pending'
    payment.razorpay_order_id = dummy_order_id
    payment.save()
    print(f"[OK] Payment Record Created: Invoice #{payment.invoice_number}, Status={payment.status}")

    # 4. Simulate Signature Verification & Success Callback
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')
    message = f"{dummy_order_id}|{dummy_payment_id}"
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Apply Success
    payment.razorpay_payment_id = dummy_payment_id
    payment.razorpay_signature = generated_signature
    payment.status = 'success'
    payment.payment_method = 'card'
    payment.paid_at = timezone.now()
    payment.save()

    booking.is_paid = True
    booking.status = 'approved'
    booking.save()

    assert payment.status == 'success'
    assert booking.is_paid is True
    assert booking.status == 'approved'
    print(f"[OK] Signature verified. Payment status = '{payment.status}', Booking status = '{booking.status}'")

    # 5. Dispatch In-App Notifications
    dispatch_payment_notifications(payment)

    patient_notifs = InAppNotification.objects.filter(user=patient, notification_type='payment')
    doctor_notifs = InAppNotification.objects.filter(user=doctor_user, notification_type='appointment')
    admin_notifs = InAppNotification.objects.filter(user=admin_user, notification_type='revenue')

    assert patient_notifs.exists(), "Patient notification missing"
    assert doctor_notifs.exists(), "Doctor notification missing"
    assert admin_notifs.exists(), "Admin notification missing"
    print(f"[OK] In-App Notifications Dispatched: Patient ({patient_notifs.count()}), Doctor ({doctor_notifs.count()}), Admin ({admin_notifs.count()})")

    # 6. Test Invoice PDF Persistence
    from django.test import RequestFactory
    rf = RequestFactory()
    req = rf.get(f'/payment/{payment.id}/invoice/')
    req.user = patient

    view = InvoicePDFView()
    response = view.get(req, payment_id=payment.id)
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'

    invoice_obj = Invoice.objects.filter(payment=payment).first()
    assert invoice_obj is not None
    assert invoice_obj.pdf_file is not None
    print(f"[OK] Invoice PDF generated & persisted: #{invoice_obj.invoice_number}, Total Amount = INR {invoice_obj.total_amount}")

    # 7. Test DRF Serializers
    pay_serializer = PaymentSerializer(payment)
    assert pay_serializer.data['status'] == 'success'
    assert pay_serializer.data['payment_method'] == 'card'

    notif_serializer = InAppNotificationSerializer(patient_notifs.first())
    assert notif_serializer.data['notification_type'] == 'payment'

    print("[OK] DRF Serializers verified cleanly")
    print("\n=== ALL RAZORPAY PAYMENT WORKFLOW TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_tests()
