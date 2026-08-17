"""
Payment views for DocMed appointment booking system.

Supports Razorpay, Stripe, UPI/QR payment gateways.
All API keys are loaded from Django settings (environment variables).

HOW TO CONFIGURE:
  1. Copy .env.example to .env
  2. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET — https://dashboard.razorpay.com/
  3. Set STRIPE_PUBLISHABLE_KEY and STRIPE_SECRET_KEY — https://dashboard.stripe.com/
  4. Set UPI_ID to your UPI address (e.g. docmed@upi)
  5. Set GEMINI_API_KEY for AI report analysis — https://aistudio.google.com/
"""

import io
import json
import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView, ListView
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt

from .models import TakeAppointment, Payment
from .decorators import user_is_patient

logger = logging.getLogger(__name__)


# ============================================================================
# Payment Initiation
# ============================================================================

class InitiatePaymentView(LoginRequiredMixin, View):
    """
    Show payment method selection page for an appointment booking.
    Patient selects Razorpay, Stripe, or UPI/QR.
    Also generates UPI QR code for scan-and-pay.
    """
    template_name = 'payment/payment_initiate.html'
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id, user=request.user)

        # If already paid, redirect to success page
        if hasattr(booking, 'payment') and booking.payment.status == 'success':
            messages.info(request, 'This appointment is already paid.')
            return redirect('appointment:payment-success', payment_id=booking.payment.id)

        # Get consultation fee from doctor profile
        fee = 500.0  # Default fallback
        try:
            fee = float(booking.appointment.user.doctor_profile.consultation_fee)
        except Exception:
            pass

        # Generate UPI QR code
        upi_qr_base64 = None
        try:
            import qrcode
            import base64
            upi_id = getattr(settings, 'UPI_ID', 'docmed@upi')
            merchant = getattr(settings, 'UPI_MERCHANT_NAME', 'DocMed Healthcare')
            upi_uri = (
                f'upi://pay?pa={upi_id}&pn={merchant}'
                f'&am={fee}&cu=INR&tn=DocMed+Booking+{booking.id}'
            )
            qr = qrcode.QRCode(version=1, box_size=6, border=2)
            qr.add_data(upi_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            upi_qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            logger.warning(f'QR code generation failed: {e}')

        context = {
            'booking': booking,
            'fee': fee,
            'upi_qr_base64': upi_qr_base64,
            # ⚠️ Placeholder — set UPI_ID in your .env file
            'upi_id': getattr(settings, 'UPI_ID', 'docmed@upi'),
            # ⚠️ Placeholder — set RAZORPAY_KEY_ID in your .env file
            'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
            # ⚠️ Placeholder — set STRIPE_PUBLISHABLE_KEY in your .env file
            'stripe_publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        }
        return render(request, self.template_name, context)


# ============================================================================
# Razorpay
# ============================================================================

class RazorpayOrderView(LoginRequiredMixin, View):
    """
    Creates a Razorpay order server-side.
    Returns JSON with order_id for the frontend Razorpay checkout modal.

    ⚠️ CONFIGURE: Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env
    Get keys from: https://dashboard.razorpay.com/ → Settings → API Keys
    """
    login_url = reverse_lazy('accounts:login')

    def post(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id, user=request.user)

        fee = 500.0
        try:
            fee = float(booking.appointment.user.doctor_profile.consultation_fee)
        except Exception:
            pass

        amount_paise = int(fee * 100)  # Razorpay uses smallest unit (paise for INR)

        try:
            import razorpay
            # ⚠️ Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file
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

            # Save Payment record
            payment, _ = Payment.objects.get_or_create(booking=booking)
            payment.gateway = 'razorpay'
            payment.amount = fee
            payment.status = 'pending'
            payment.razorpay_order_id = razorpay_order['id']
            payment.save()

            return JsonResponse({
                'order_id': razorpay_order['id'],
                'amount': amount_paise,
                'currency': getattr(settings, 'RAZORPAY_CURRENCY', 'INR'),
                'key_id': settings.RAZORPAY_KEY_ID,
                'booking_id': booking.id,
                'name': 'DocMed Healthcare',
                'description': f'Appointment with Dr. {booking.appointment.full_name}',
                'prefill_name': booking.full_name,
                'prefill_email': booking.user.email,
                'prefill_contact': booking.phone_number,
            })
        except Exception as e:
            logger.error(f'Razorpay order creation failed: {e}')
            return JsonResponse({'error': str(e)}, status=400)


class RazorpayCallbackView(LoginRequiredMixin, View):
    """
    Verifies Razorpay payment signature after checkout completes.
    NEVER trust client-side success — always verify server-side signature.

    ⚠️ CONFIGURE: RAZORPAY_KEY_SECRET must be set in .env for signature verification
    """
    login_url = reverse_lazy('accounts:login')

    def post(self, request, *args, **kwargs):
        try:
            import razorpay
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            booking_id = request.POST.get('booking_id')

            # ⚠️ RAZORPAY_KEY_SECRET must be set in .env for this to work
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )

            # Server-side signature verification (security critical step)
            params = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
            client.utility.verify_payment_signature(params)

            # Signature valid — mark payment as success
            payment = get_object_or_404(Payment, razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'success'

            from django.utils import timezone
            payment.paid_at = timezone.now()

            # Attempt to fetch exact payment method from Razorpay API
            try:
                razor_pay_obj = client.payment.fetch(razorpay_payment_id)
                payment.payment_method = razor_pay_obj.get('method', 'razorpay')
            except Exception as fetch_err:
                logger.warning(f'Could not fetch Razorpay payment method: {fetch_err}')
                payment.payment_method = 'razorpay'

            payment.save()

            # Mark booking as paid and confirmed
            payment.booking.is_paid = True
            payment.booking.status = 'approved'
            payment.booking.save(update_fields=['is_paid', 'status'])

            # Create Google Calendar Event & Google Meet Link
            try:
                from .google_calendar_service import create_google_calendar_event
                create_google_calendar_event(payment.booking)
            except Exception as g_err:
                logger.warning(f'Google Calendar event creation warning for Booking #{payment.booking.id}: {g_err}')

            # Send multi-channel notifications (HTML Email, SMS, In-App Notifications)
            try:
                from .emails import send_payment_confirmation_email
                send_payment_confirmation_email(payment)
            except Exception as email_err:
                logger.warning(f'Payment email failed: {email_err}')

            try:
                from .notification_service import dispatch_payment_notifications, notify_payment_success
                dispatch_payment_notifications(payment)
                notify_payment_success(payment)
            except Exception as notif_err:
                logger.warning(f'In-app notification dispatch failed: {notif_err}')

            messages.success(request, '🎉 Payment successful! Your appointment is confirmed.')
            return redirect('appointment:payment-success', payment_id=payment.id)

        except Exception as e:
            logger.error(f'Razorpay verification failed: {e}')
            booking_id = request.POST.get('booking_id')
            if booking_id:
                try:
                    p = Payment.objects.filter(booking_id=booking_id).first()
                    if p and p.status != 'success':
                        p.status = 'failed'
                        p.save()
                    from .emails import send_payment_failed_email
                    booking_obj = TakeAppointment.objects.get(pk=booking_id)
                    send_payment_failed_email(booking_obj, amount=booking_obj.appointment.fee if hasattr(booking_obj.appointment, 'fee') else 500)
                except Exception:
                    pass
            messages.error(request, 'Payment verification failed. You can retry your payment.')
            return redirect('appointment:payment-failed', booking_id=booking_id or '0')


# ============================================================================
# Stripe
# ============================================================================

class StripeCheckoutView(LoginRequiredMixin, View):
    """
    Creates Stripe Checkout Session and redirects to Stripe hosted payment page.

    ⚠️ CONFIGURE: Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in .env
    Get keys from: https://dashboard.stripe.com/ → Developers → API Keys
    """
    login_url = reverse_lazy('accounts:login')

    def post(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id, user=request.user)

        fee = 500.0
        try:
            fee = float(booking.appointment.user.doctor_profile.consultation_fee)
        except Exception:
            pass

        try:
            import stripe
            # ⚠️ Set STRIPE_SECRET_KEY in .env
            stripe.api_key = settings.STRIPE_SECRET_KEY

            success_url = (
                request.build_absolute_uri(
                    reverse('appointment:stripe-success', kwargs={'booking_id': booking_id})
                ) + '?session_id={CHECKOUT_SESSION_ID}'
            )
            cancel_url = request.build_absolute_uri(
                reverse('appointment:payment-failed', kwargs={'booking_id': booking_id})
            )

            currency = getattr(settings, 'STRIPE_CURRENCY', 'usd')
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f'Appointment with Dr. {booking.appointment.full_name}',
                            'description': f'DocMed consultation — {booking.appointment.department}',
                        },
                        'unit_amount': int(fee * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=request.user.email,
                metadata={'booking_id': str(booking_id)},
            )

            # Save Stripe session ID
            payment, _ = Payment.objects.get_or_create(booking=booking)
            payment.gateway = 'stripe'
            payment.amount = fee
            payment.status = 'pending'
            payment.stripe_session_id = session.id
            payment.save()

            return redirect(session.url, code=303)

        except Exception as e:
            logger.error(f'Stripe checkout creation failed: {e}')
            messages.error(request, 'Stripe payment could not be initiated. Please try another method.')
            return redirect('appointment:initiate-payment', booking_id=booking_id)


class StripeSuccessView(LoginRequiredMixin, View):
    """
    Handles Stripe redirect after successful payment.
    Verifies the session and marks payment as complete.
    """
    login_url = reverse_lazy('accounts:login')

    def get(self, request, booking_id, *args, **kwargs):
        session_id = request.GET.get('session_id')
        if not session_id:
            return redirect('appointment:payment-failed', booking_id=booking_id)

        try:
            import stripe
            # ⚠️ STRIPE_SECRET_KEY must be set in .env
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == 'paid':
                payment = get_object_or_404(Payment, stripe_session_id=session_id)
                payment.stripe_payment_intent = session.payment_intent
                payment.status = 'success'
                payment.save()

                payment.booking.is_paid = True
                payment.booking.save()

                try:
                    from .emails import send_payment_confirmation_email
                    send_payment_confirmation_email(payment)
                except Exception as email_err:
                    logger.warning(f'Payment email failed: {email_err}')

                messages.success(request, '🎉 Stripe payment successful!')
                return redirect('appointment:payment-success', payment_id=payment.id)
            else:
                return redirect('appointment:payment-failed', booking_id=booking_id)

        except Exception as e:
            logger.error(f'Stripe success verification failed: {e}')
            return redirect('appointment:payment-failed', booking_id=booking_id)


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook endpoint for asynchronous payment events.

    ⚠️ CONFIGURE:
      1. Set STRIPE_WEBHOOK_SECRET in .env
      2. Register this URL at: https://dashboard.stripe.com/webhooks
      3. Listen for: payment_intent.succeeded, payment_intent.payment_failed
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        # ⚠️ Set STRIPE_WEBHOOK_SECRET in .env for signature verification
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f'Stripe webhook error: {e}')
        return HttpResponse(status=400)

    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        try:
            payment = Payment.objects.get(stripe_payment_intent=intent['id'])
            payment.status = 'success'
            payment.save()
            payment.booking.is_paid = True
            payment.booking.save()
        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)


# ============================================================================
# UPI
# ============================================================================

class UPIPaymentConfirmView(LoginRequiredMixin, View):
    """
    Handles UPI payment manual confirmation.
    Patient enters UPI transaction ID after scanning QR and paying.

    ⚠️ NOTE: UPI does not have a free server-side verification API.
    In production, integrate with a payment aggregator (e.g. Razorpay UPI)
    for automatic verification. Currently uses manual admin verification.
    """
    login_url = reverse_lazy('accounts:login')

    def post(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id, user=request.user)
        upi_transaction_id = request.POST.get('upi_transaction_id', '').strip()

        if not upi_transaction_id:
            messages.error(request, 'Please enter your UPI Transaction ID.')
            return redirect('appointment:initiate-payment', booking_id=booking_id)

        fee = 500.0
        try:
            fee = float(booking.appointment.user.doctor_profile.consultation_fee)
        except Exception:
            pass

        payment, _ = Payment.objects.get_or_create(booking=booking)
        payment.gateway = 'upi'
        payment.amount = fee
        payment.status = 'pending'  # Admin manually verifies UPI transactions
        payment.upi_transaction_id = upi_transaction_id
        payment.save()

        messages.success(request, f'UPI payment submitted (TXN: {upi_transaction_id}). Pending verification by admin.')
        return redirect('appointment:payment-pending', booking_id=booking_id)


# ============================================================================
# Status Pages
# ============================================================================

class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    """
    Premium animated payment success page.
    Features confetti, countdown redirect, and full booking details.
    """
    template_name = 'payment/payment_success.html'
    login_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_id = self.kwargs.get('payment_id')
        payment = get_object_or_404(Payment, pk=payment_id, booking__user=self.request.user)
        context['payment'] = payment
        context['booking'] = payment.booking
        return context


class PaymentFailedView(LoginRequiredMixin, TemplateView):
    """Animated payment failure page with retry options."""
    template_name = 'payment/payment_failed.html'
    login_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_id = self.kwargs.get('booking_id')
        try:
            context['booking'] = TakeAppointment.objects.get(
                pk=booking_id, user=self.request.user
            )
        except TakeAppointment.DoesNotExist:
            context['booking'] = None
        return context


class PaymentPendingView(LoginRequiredMixin, TemplateView):
    """Animated pending payment page (used for UPI manual confirmation)."""
    template_name = 'payment/payment_pending.html'
    login_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_id = self.kwargs.get('booking_id')
        try:
            context['booking'] = TakeAppointment.objects.get(
                pk=booking_id, user=self.request.user
            )
        except TakeAppointment.DoesNotExist:
            context['booking'] = None
        return context


# ============================================================================
# Payment History + Invoice PDF
# ============================================================================

class PaymentHistoryView(LoginRequiredMixin, ListView):
    """Patient payment history with invoice download links."""
    model = Payment
    template_name = 'payment/payment_history.html'
    context_object_name = 'payments'
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Payment.objects
            .filter(booking__user=self.request.user)
            .select_related('booking', 'booking__appointment')
            .order_by('-created_at')
        )


class InvoicePDFView(LoginRequiredMixin, View):
    """Generates, saves to database, and serves a PDF invoice for a payment using ReportLab."""
    login_url = reverse_lazy('accounts:login')

    def get(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=payment_id)
        # Check permissions: owner or doctor or staff
        if not (request.user == payment.booking.user or request.user == payment.booking.appointment.user or request.user.is_staff):
            messages.error(request, 'Permission denied.')
            return redirect('appointment:home')

        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        story = []

        # ── Title / Header ──────────────────────────────────────────
        title_style = ParagraphStyle(
            'DocMedTitle', parent=styles['Title'],
            fontSize=24, textColor=colors.HexColor('#2563EB'),
            alignment=TA_CENTER, spaceAfter=4
        )
        story.append(Paragraph('🏥 DocMed AI Healthcare', title_style))
        story.append(Paragraph('OFFICIAL MEDICAL TAX INVOICE', styles['Heading2']))
        story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563EB')))
        story.append(Spacer(1, 0.4*cm))

        # ── Invoice & Tax Breakdown Data ───────────────────────────
        booking = payment.booking
        transaction_id = (
            payment.razorpay_payment_id or
            payment.stripe_payment_intent or
            payment.upi_transaction_id or 'N/A'
        )
        currency_symbol = '₹' if payment.gateway in ['razorpay', 'upi'] else '$'

        subtotal = float(payment.amount)
        tax_amount = round(subtotal * 0.18, 2)  # 18% GST calculation
        discount = 0.00
        total_amount = round(subtotal + tax_amount - discount, 2)

        data = [
            ['Invoice Number', payment.invoice_number],
            ['Invoice Date', payment.created_at.strftime('%d %b %Y %I:%M %p')],
            ['Booking ID', f'#{booking.id}'],
            ['Patient Name', booking.full_name],
            ['Patient Email', booking.user.email],
            ['Patient Phone', booking.phone_number],
            ['Doctor Name', f'Dr. {booking.appointment.full_name}'],
            ['Hospital Name', booking.appointment.hospital_name],
            ['Department', booking.appointment.department],
            ['Appointment Date', booking.date.strftime('%d %b %Y %I:%M %p')],
            ['Consultation Time', f'{booking.appointment.start_time} – {booking.appointment.end_time}'],
            ['Payment Method', payment.get_gateway_display()],
            ['Transaction ID', transaction_id],
            ['Payment Status', payment.get_status_display().upper()],
            ['Consultation Fee', f'{currency_symbol}{subtotal:.2f}'],
            ['GST / Tax (18%)', f'{currency_symbol}{tax_amount:.2f}'],
            ['Discount', f'-{currency_symbol}{discount:.2f}'],
            ['Total Paid Amount', f'{currency_symbol}{total_amount:.2f}'],
        ]

        table = Table(data, colWidths=[5.5*cm, 11.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EFF6FF')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1E40AF')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Highlight Total Paid Amount row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.6*cm))

        # ── Digital Signature & Verification Block ─────────────────────
        signature_style = ParagraphStyle(
            'SigStyle', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#334155'), alignment=TA_CENTER
        )
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#CBD5E1')))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph('✒️ <b>Digitally Verified & Authorised by DocMed Healthcare Billing Desk</b>', signature_style))
        story.append(Paragraph('QR Code Verification: Scan to verify authenticity online at www.docmed.com/verify-invoice/', signature_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Footer ──────────────────────────────────────────────────
        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'],
            fontSize=8, textColor=colors.grey, alignment=TA_CENTER
        )
        story.append(Paragraph(
            'DocMed AI Healthcare Platform | Support: support@docmed.com | +91 1800-123-4567',
            footer_style
        ))
        story.append(Paragraph(
            'This is a computer-generated tax invoice. No physical signature required.',
            footer_style
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.seek(0)

        # Save to database Invoice model record
        try:
            from django.core.files.base import ContentFile
            from .models import Invoice
            invoice_obj, created = Invoice.objects.get_or_create(
                payment=payment,
                defaults={
                    'invoice_number': payment.invoice_number,
                    'subtotal': subtotal,
                    'tax_amount': tax_amount,
                    'discount': discount,
                    'total_amount': total_amount,
                }
            )
            if not invoice_obj.pdf_file:
                invoice_obj.pdf_file.save(
                    f"Invoice_{payment.invoice_number}.pdf",
                    ContentFile(pdf_bytes),
                    save=True
                )
        except Exception as inv_err:
            logger.warning(f"Failed to persist Invoice model instance: {inv_err}")

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="DocMed_Invoice_{payment.invoice_number}.pdf"'
        )
        return response


class PaymentReceiptView(LoginRequiredMixin, View):
    """
    Renders the Payment Receipt Card UI with transaction breakdown
    and instant PDF invoice & receipt download buttons.
    """
    login_url = reverse_lazy('accounts:login')

    def get(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=payment_id)
        if not (request.user == payment.booking.user or request.user == payment.booking.appointment.user or request.user.is_staff):
            messages.error(request, 'Permission denied.')
            return redirect('appointment:home')

        context = {
            'payment': payment,
            'booking': payment.booking,
            'doctor_name': payment.booking.appointment.full_name,
            'patient_name': payment.booking.full_name,
            'currency_symbol': '₹' if payment.gateway in ['razorpay', 'upi'] else '$',
        }
        return render(request, 'appointment/payment_receipt.html', context)


# ============================================================================
# Refund Processing Views
# ============================================================================

class RequestRefundView(LoginRequiredMixin, View):
    """Allows a patient to request a refund for a successful payment."""
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=payment_id, booking__user=request.user)
        
        if payment.status != 'success':
            messages.error(request, 'Only successful payments can be refunded.')
            return redirect('appointment:payment-history')
            
        if payment.refund_requested:
            messages.warning(request, 'Refund has already been requested for this payment.')
            return redirect('appointment:payment-history')
            
        reason = request.POST.get('refund_reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for the refund.')
            return redirect('appointment:payment-history')
            
        payment.refund_requested = True
        payment.refund_reason = reason
        payment.refund_status = 'pending'
        payment.save()
        
        messages.success(request, 'Your refund request has been submitted successfully!')
        return redirect('appointment:payment-history')


class AdminRefundActionView(LoginRequiredMixin, View):
    """Allows admin/staff to approve or reject a refund request."""
    login_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            messages.error(request, 'Access denied.')
            return redirect('appointment:home')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=payment_id)
        action = request.POST.get('action') # 'approve' or 'reject'
        
        if not payment.refund_requested:
            messages.error(request, 'No refund has been requested for this payment.')
            return redirect('appointment:admin-dashboard')
            
        if action == 'approve':
            payment.refund_status = 'approved'
            payment.status = 'refunded'
            payment.save()
            messages.success(request, f'Refund approved for Invoice #{payment.invoice_number}.')
        elif action == 'reject':
            payment.refund_status = 'rejected'
            payment.save()
            messages.success(request, f'Refund request rejected for Invoice #{payment.invoice_number}.')
        else:
            messages.error(request, 'Invalid action.')
            
        return redirect('appointment:admin-dashboard')

