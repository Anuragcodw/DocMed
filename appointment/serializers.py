"""
Serializers for DocMed appointment system REST APIs.

Provides serializers for Payments, Invoices, In-App Notifications,
and Razorpay Order creation & signature verification.
"""

from rest_framework import serializers
from .models import Payment, Invoice, InAppNotification, TakeAppointment


class TakeAppointmentSummarySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='appointment.full_name', read_only=True)
    department = serializers.CharField(source='appointment.department', read_only=True)
    hospital_name = serializers.CharField(source='appointment.hospital_name', read_only=True)
    fee = serializers.SerializerMethodField()

    class Meta:
        model = TakeAppointment
        fields = [
            'id', 'full_name', 'phone_number', 'date', 'status',
            'is_paid', 'doctor_name', 'department', 'hospital_name', 'fee',
        ]

    def get_fee(self, obj):
        try:
            return float(obj.appointment.user.doctor_profile.consultation_fee)
        except Exception:
            return 500.0


class PaymentSerializer(serializers.ModelSerializer):
    booking = TakeAppointmentSummarySerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'booking', 'gateway', 'status', 'amount', 'currency',
            'razorpay_order_id', 'razorpay_payment_id', 'payment_method',
            'paid_at', 'invoice_number', 'created_at', 'updated_at',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'subtotal', 'tax_amount',
            'discount', 'total_amount', 'pdf_url', 'created_at',
        ]

    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = [
            'id', 'title', 'message', 'notification_type',
            'is_read', 'link', 'created_at',
        ]


class RazorpayCreateOrderRequestSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)


class RazorpayVerifyPaymentRequestSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)
    razorpay_order_id = serializers.CharField(required=True)
    razorpay_payment_id = serializers.CharField(required=True)
    razorpay_signature = serializers.CharField(required=True)
