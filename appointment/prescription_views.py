import io
import os
import logging
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView
from django.db.models import Q

from .models import Prescription, PrescriptionItem, TakeAppointment
from .decorators import user_is_doctor, user_is_patient

logger = logging.getLogger(__name__)

# ============================================================================
# Create Prescription
# ============================================================================

class CreatePrescriptionView(LoginRequiredMixin, View):
    """
    Doctor creates a prescription for a completed booking.
    Supports detailed multi-medicine listings, dosage instructions, and timings.
    """
    template_name = 'appointment/prescription_create.html'
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(
            TakeAppointment, pk=booking_id,
            appointment__user=request.user
        )
        prescription = getattr(booking, 'prescription', None)
        context = {
            'booking': booking,
            'prescription': prescription,
            'frequency_choices': PrescriptionItem.FREQUENCY_CHOICES,
        }
        return render(request, self.template_name, context)

    def post(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(
            TakeAppointment, pk=booking_id,
            appointment__user=request.user
        )

        diagnosis = request.POST.get('diagnosis', '').strip()
        symptoms = request.POST.get('symptoms', '').strip()
        diagnosis_notes = request.POST.get('diagnosis_notes', '').strip()
        advice = request.POST.get('advice', '').strip()
        lab_tests = request.POST.get('lab_tests', '').strip()
        follow_up_date = request.POST.get('follow_up_date') or None

        # Create or update Prescription
        prescription, created = Prescription.objects.update_or_create(
            booking=booking,
            defaults={
                'diagnosis': diagnosis,
                'symptoms': symptoms,
                'diagnosis_notes': diagnosis_notes,
                'advice': advice,
                'lab_tests': lab_tests,
                'follow_up_date': follow_up_date,
            }
        )

        # Clear existing items and rebuild from POST data
        prescription.items.all().delete()

        # Parse medicine items
        medicine_names = request.POST.getlist('medicine_name[]')
        dosages = request.POST.getlist('dosage[]')
        frequencies = request.POST.getlist('frequency[]')
        mornings = request.POST.getlist('morning[]')
        afternoons = request.POST.getlist('afternoon[]')
        nights = request.POST.getlist('night[]')
        before_foods = request.POST.getlist('before_food[]')
        number_of_days_list = request.POST.getlist('number_of_days[]')
        instructions_list = request.POST.getlist('instructions[]')
        notes_list = request.POST.getlist('med_notes[]')

        items_created = 0
        for i, name in enumerate(medicine_names):
            if name.strip():
                # Extract values with safe bounds checks
                m = mornings[i] == '1' if i < len(mornings) else False
                a = afternoons[i] == '1' if i < len(afternoons) else False
                n = nights[i] == '1' if i < len(nights) else False
                bf = before_foods[i] == '1' if i < len(before_foods) else False
                
                try:
                    days = int(number_of_days_list[i]) if i < len(number_of_days_list) else 1
                except ValueError:
                    days = 1

                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medicine_name=name.strip(),
                    dosage=dosages[i] if i < len(dosages) else '',
                    frequency=frequencies[i] if i < len(frequencies) else 'twice_daily',
                    morning=m,
                    afternoon=a,
                    night=n,
                    before_food=bf,
                    number_of_days=days,
                    duration=f"{days} Days",
                    instructions=instructions_list[i] if i < len(instructions_list) else '',
                    notes=notes_list[i] if i < len(notes_list) else ''
                )
                items_created += 1

        # Generate QR Code pointing to prescription details page
        try:
            detail_url = request.build_absolute_uri(
                reverse('appointment:prescription-detail', kwargs={'booking_id': booking.id})
            )
            qr = qrcode.QRCode(version=1, box_size=5, border=1)
            qr.add_data(detail_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            
            qr_buffer = io.BytesIO()
            img.save(qr_buffer, format='PNG')
            
            prescription.qr_code.save(
                f"qr_prescription_{booking.id}.png",
                ContentFile(qr_buffer.getvalue()),
                save=False
            )
            prescription.save()
        except Exception as e:
            logger.error(f"Failed to generate prescription QR code: {str(e)}")

        messages.success(
            request,
            f'Prescription successfully saved with {items_created} medicine(s) for {booking.full_name}.'
        )
        return redirect('appointment:doctor-appointment')


# ============================================================================
# Prescription Detail
# ============================================================================

class PrescriptionDetailView(LoginRequiredMixin, View):
    """Patient or Doctor views their prescription details."""
    template_name = 'appointment/prescription_detail.html'
    login_url = reverse_lazy('accounts:login')

    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id)

        # Secure prescription access restriction
        is_patient = booking.user == request.user
        is_doctor = booking.appointment.user == request.user
        if not is_patient and not is_doctor:
            raise Http404("You do not have permission to access this prescription.")

        prescription = get_object_or_404(Prescription, booking=booking)
        context = {
            'booking': booking,
            'prescription': prescription,
            'items': prescription.items.all(),
            'is_doctor': is_doctor,
        }
        return render(request, self.template_name, context)


# ============================================================================
# ReportLab PDF Generation
# ============================================================================

class PrescriptionPDFView(LoginRequiredMixin, View):
    """
    Generates a beautifully formatted PDF prescription using ReportLab.
    Accessible by both patient and doctor.
    """
    login_url = reverse_lazy('accounts:login')

    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(TakeAppointment, pk=booking_id)

        # Secure prescription access restriction
        is_patient = booking.user == request.user
        is_doctor = booking.appointment.user == request.user
        if not is_patient and not is_doctor:
            raise Http404("You do not have permission to access this prescription.")

        prescription = get_object_or_404(Prescription, booking=booking)
        items = prescription.items.all()

        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer, HRFlowable, Image
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )

        styles = getSampleStyleSheet()
        story = []
        
        # Primary Color Theme: Indigo + Soft Cyan details
        indigo = colors.HexColor('#4f46e5')
        soft_indigo = colors.HexColor('#f5f3ff')
        dark_gray = colors.HexColor('#1f2937')
        border_color = colors.HexColor('#e5e7eb')

        # ── Title ──────────────────────────────────────────────────
        title_style = ParagraphStyle(
            'Header', parent=styles['Title'],
            fontSize=20, textColor=indigo, alignment=TA_CENTER
        )
        story.append(Paragraph('🏥 DocMed Healthcare — Prescription', title_style))
        story.append(HRFlowable(width='100%', thickness=2, color=indigo, spaceAfter=15))

        # ── Patient / Doctor Meta Table ─────────────────────────────
        doc_profile = getattr(booking.appointment.user, 'doctor_profile', None)
        info_data = [
            [
                Paragraph(f"<b>Patient Name:</b> {booking.full_name}<br/><b>Gender:</b> {booking.user.gender|default:'N/A'}<br/><b>Phone:</b> {booking.phone_number}", styles['Normal']),
                Paragraph(f"<b>Doctor:</b> Dr. {booking.appointment.full_name}<br/><b>Specialization:</b> {booking.appointment.department}<br/><b>Hospital:</b> {booking.appointment.hospital_name}", styles['Normal'])
            ],
            [
                Paragraph(f"<b>Date:</b> {booking.date.strftime('%d %b %Y')}", styles['Normal']),
                Paragraph(f"<b>Follow-up Date:</b> {prescription.follow_up_date.strftime('%d %b %Y') if prescription.follow_up_date else 'As needed'}", styles['Normal'])
            ]
        ]
        info_table = Table(info_data, colWidths=[9*cm, 9*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), soft_indigo),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Symptoms & Diagnosis ────────────────────────────────────
        if prescription.symptoms:
            story.append(Paragraph('📋 Symptoms', styles['Heading3']))
            story.append(Paragraph(prescription.symptoms, styles['Normal']))
            story.append(Spacer(1, 0.3*cm))

        if prescription.diagnosis:
            story.append(Paragraph('🩺 Diagnosis', styles['Heading3']))
            story.append(Paragraph(prescription.diagnosis, styles['Normal']))
            story.append(Spacer(1, 0.3*cm))

        # ── Medications Table ───────────────────────────────────────
        story.append(Paragraph('💊 Prescribed Medications', styles['Heading3']))
        story.append(Spacer(1, 0.2*cm))

        if items:
            med_headers = ['#', 'Medicine Name', 'Dosage', 'Timing (M-A-N)', 'Meal', 'Days', 'Notes']
            med_data = [med_headers]
            for idx, item in enumerate(items, 1):
                timing_str = f"{'1' if item.morning else '0'} - {'1' if item.afternoon else '0'} - {'1' if item.night else '0'}"
                meal_str = "Before Food" if item.before_food else "After Food"
                med_data.append([
                    str(idx),
                    item.medicine_name,
                    item.dosage,
                    timing_str,
                    meal_str,
                    f"{item.number_of_days} Days",
                    item.notes or '—'
                ])

            med_table = Table(med_data, colWidths=[0.8*cm, 4.5*cm, 2.2*cm, 2.5*cm, 2.5*cm, 1.8*cm, 3.7*cm])
            med_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), indigo),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(med_table)
        else:
            story.append(Paragraph('No medications prescribed.', styles['Normal']))

        story.append(Spacer(1, 0.4*cm))

        # ── Advice & Labs ──────────────────────────────────────────
        if prescription.advice:
            story.append(Paragraph('📝 Additional Advice', styles['Heading3']))
            story.append(Paragraph(prescription.advice, styles['Normal']))
            story.append(Spacer(1, 0.3*cm))

        if prescription.lab_tests:
            story.append(Paragraph('🔬 Recommended Lab Tests', styles['Heading3']))
            story.append(Paragraph(prescription.lab_tests, styles['Normal']))
            story.append(Spacer(1, 0.3*cm))

        story.append(Spacer(1, 0.6*cm))

        # ── Signature & QR Code Blocks ──────────────────────────────
        sig_data = []
        
        # QR Code Generation cell
        qr_cell = Paragraph('Scan to Verify Prescription', styles['Normal'])
        if prescription.qr_code:
            try:
                qr_img = Image(prescription.qr_code.path, width=2.5*cm, height=2.5*cm)
                qr_cell = qr_img
            except Exception:
                pass

        # Digital Signature cell
        sig_cell = Paragraph('Doctor Signature Placeholder', styles['Normal'])
        if doc_profile and doc_profile.digital_signature:
            try:
                sig_img = Image(doc_profile.digital_signature.path, width=3.5*cm, height=1.5*cm)
                sig_cell = sig_img
            except Exception:
                pass

        sig_data = [
            [qr_cell, sig_cell],
            [Paragraph('<b>Secure Verification QR Code</b>', styles['Normal']), Paragraph('<b>Dr. Signature</b>', styles['Normal'])]
        ]
        
        sig_table = Table(sig_data, colWidths=[9*cm, 9*cm])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(sig_table)

        # Disclaimer
        story.append(Spacer(1, 0.5*cm))
        disc_style = ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        story.append(Paragraph('⚠️ This is a digitally signed electronic prescription. Consult your healthcare provider prior to starting medication.', disc_style))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Prescription_{booking_id}.pdf"'
        return response


# ============================================================================
# Prescription History List
# ============================================================================

class PrescriptionHistoryView(LoginRequiredMixin, ListView):
    """
    Searchable and filterable listing of past prescriptions for Patients and Doctors.
    """
    model = Prescription
    template_name = 'appointment/prescription_history.html'
    context_object_name = 'prescriptions'
    login_url = reverse_lazy('accounts:login')

    def get_queryset(self):
        user = self.request.user
        search_query = self.request.GET.get('search', '').strip()
        date_filter = self.request.GET.get('date_filter', '').strip()

        # Restrict rows depending on role type
        if user.role == 'patient':
            qs = Prescription.objects.filter(booking__user=user)
        elif user.role == 'doctor':
            qs = Prescription.objects.filter(booking__appointment__user=user)
        else:
            qs = Prescription.objects.none()

        # Search matching medicine names or symptoms
        if search_query:
            qs = qs.filter(
                Q(diagnosis__icontains=search_query) |
                Q(symptoms__icontains=search_query) |
                Q(items__medicine_name__icontains=search_query)
            ).distinct()

        # Apply specific date filters
        if date_filter:
            qs = qs.filter(created_at__date=date_filter)

        return qs.select_related('booking', 'booking__appointment', 'booking__appointment__user')
