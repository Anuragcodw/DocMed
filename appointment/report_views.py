"""
Medical Report Center views for DocMed healthcare platform.

Patients can upload, view, analyze, and manage their medical reports.
Supports PDF, PNG, JPG formats with AI-powered analysis via Gemini API.

HOW TO CONFIGURE:
  1. Set GEMINI_API_KEY in .env — https://aistudio.google.com/app/apikey
  2. Set AI_ANALYSIS_ENABLED=True in .env to enable AI
  3. Set MEDICAL_REPORT_MAX_SIZE_MB to control upload size limit
"""

import io
import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView

from .models import MedicalReport, REPORT_TYPE_CHOICES, ALLOWED_REPORT_EXTENSIONS
from .decorators import user_is_patient

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    'application/pdf': 'pdf',
    'image/png': 'png',
    'image/jpeg': 'jpeg',
    'image/jpg': 'jpg',
}

MAX_SIZE_BYTES = getattr(settings, 'MEDICAL_REPORT_MAX_SIZE_MB', 10) * 1024 * 1024


# ============================================================================
# Report Center (Main Page)
# ============================================================================

class MedicalReportCenterView(LoginRequiredMixin, TemplateView):
    """
    Main Medical Report Center page.
    Shows all patient reports with filters, search, drag-drop upload area,
    and report history. Completely new page — does not replace any existing page.
    """
    template_name = 'reports/report_center.html'
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = MedicalReport.objects.filter(patient=self.request.user)

        # ML-Enhanced Search
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            from django.db.models import Q
            from ml_models.preprocessing import MedicalTextPreprocessor
            from ml_models.report_analysis import ReportClassifier

            # 1. Clean clinical keywords using ML text preprocessor
            preprocessor = MedicalTextPreprocessor()
            cleaned_query = preprocessor.preprocess(search_query)

            # 2. Predict targeted report category using ML report classifier
            classifier = ReportClassifier()
            predicted_category = classifier.classify_report(cleaned_query)

            # 3. Enhanced query: search for raw query matches or predicted category matches
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(doctor_name__icontains=search_query) |
                Q(hospital_name__icontains=search_query) |
                Q(extracted_text__icontains=cleaned_query) |
                Q(report_type=predicted_category)
            )

        # Filter by type
        report_type = self.request.GET.get('type', '').strip()
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        # Pagination
        paginator = Paginator(queryset, 9)
        page = self.request.GET.get('page', 1)
        reports = paginator.get_page(page)

        context['reports'] = reports
        context['report_type_choices'] = REPORT_TYPE_CHOICES
        context['search_query'] = search_query
        context['selected_type'] = report_type
        context['total_reports'] = MedicalReport.objects.filter(patient=self.request.user).count()
        context['analyzed_reports'] = MedicalReport.objects.filter(
            patient=self.request.user, analysis_status='done'
        ).count()
        return context


# ============================================================================
# Upload
# ============================================================================

class UploadReportView(LoginRequiredMixin, View):
    """
    Handles medical report file upload with strict validation.
    Validates: file type (PDF/PNG/JPG), size (max 10MB), and filename.
    """
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        title = request.POST.get('title', '').strip()
        report_type = request.POST.get('report_type', 'other')
        doctor_name = request.POST.get('doctor_name', '').strip()
        hospital_name = request.POST.get('hospital_name', '').strip()
        report_date = request.POST.get('report_date') or None
        notes = request.POST.get('notes', '').strip()

        # ── Validation ───────────────────────────────────────────────
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('appointment:report-center')

        if not title:
            messages.error(request, 'Please provide a title for this report.')
            return redirect('appointment:report-center')

        # File type validation
        file_ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
        content_type = uploaded_file.content_type

        if file_ext not in ALLOWED_REPORT_EXTENSIONS:
            messages.error(
                request,
                f'Invalid file type: .{file_ext}. Allowed: PDF, PNG, JPG, JPEG.'
            )
            return redirect('appointment:report-center')

        # Size validation
        if uploaded_file.size > MAX_SIZE_BYTES:
            max_mb = getattr(settings, 'MEDICAL_REPORT_MAX_SIZE_MB', 10)
            messages.error(
                request,
                f'File too large ({uploaded_file.size // 1024 // 1024}MB). Maximum: {max_mb}MB.'
            )
            return redirect('appointment:report-center')

        # Malicious extension double-check (e.g. file.php.jpg)
        dangerous_exts = ['.php', '.js', '.exe', '.sh', '.bat', '.py', '.html']
        lower_name = uploaded_file.name.lower()
        if any(lower_name.endswith(ext) for ext in dangerous_exts):
            messages.error(request, 'This file type is not allowed for security reasons.')
            return redirect('appointment:report-center')

        # ── Save Report ──────────────────────────────────────────────
        report = MedicalReport.objects.create(
            patient=request.user,
            title=title,
            report_type=report_type,
            file=uploaded_file,
            doctor_name=doctor_name,
            hospital_name=hospital_name,
            report_date=report_date,
            notes=notes,
            analysis_status='pending',
        )

        messages.success(
            request,
            f'Report "{title}" uploaded successfully! Click "Analyze" to get AI insights.'
        )

        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'report_id': report.id})

        return redirect('appointment:report-detail', pk=report.id)


# ============================================================================
# Report Detail + AI Analysis
# ============================================================================

class ReportDetailView(LoginRequiredMixin, View):
    """
    Shows full report details with AI summary, voice TTS, and Ask AI chat.
    """
    template_name = 'reports/report_detail.html'
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, *args, **kwargs):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)
        context = {
            'report': report,
            'ai_enabled': getattr(settings, 'AI_ANALYSIS_ENABLED', False),
        }
        return render(request, self.template_name, context)


class AnalyzeReportView(LoginRequiredMixin, View):
    """
    Triggers AI analysis on an uploaded medical report.

    Pipeline:
    1. Extract text from PDF using pdfplumber (no external binary needed)
    2. For images: pass to Gemini Vision API directly
    3. Send extracted text/image to Google Gemini API for:
       - Summary of findings
       - Abnormal/normal values highlight
       - Easy language explanation
       - Specialist recommendation
    4. Save results to MedicalReport model

    ⚠️ CONFIGURE: Set GEMINI_API_KEY in .env to enable AI analysis
    Get key from: https://aistudio.google.com/app/apikey (free tier available)
    """
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)

        if not getattr(settings, 'AI_ANALYSIS_ENABLED', False):
            return JsonResponse({
                'status': 'error',
                'message': 'AI analysis is disabled. Set AI_ANALYSIS_ENABLED=True in .env and add your GEMINI_API_KEY.'
            }, status=400)

        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key or api_key == 'YOUR_GEMINI_API_KEY':
            return JsonResponse({
                'status': 'error',
                'message': 'GEMINI_API_KEY not configured. Add your key from https://aistudio.google.com/app/apikey to .env'
            }, status=400)

        report.analysis_status = 'analyzing'
        report.save(update_fields=['analysis_status'])

        try:
            extracted_text = self._extract_text(report)
            ai_result = self._call_gemini(report, extracted_text, api_key)

            report.extracted_text = extracted_text
            report.ai_summary = ai_result.get('summary', '')
            report.ai_findings = ai_result.get('findings', '')
            report.ai_recommendation = ai_result.get('recommendation', '')
            report.analysis_status = 'done' if (ai_result.get('summary') or extracted_text) else 'no_text'
            report.save()

            return JsonResponse({
                'status': 'done',
                'summary': report.ai_summary,
                'findings': report.ai_findings,
                'recommendation': report.ai_recommendation,
            })

        except Exception as e:
            logger.error(f'Report analysis failed for report {pk}: {e}')
            report.analysis_status = 'failed'
            report.save(update_fields=['analysis_status'])
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def _extract_text(self, report):
        """Extract text from PDF or image file using OCRReportService."""
        if not report.file or not os.path.exists(report.file.path):
            return "Unable to analyze report."

        try:
            from .ocr_service import OCRReportService
            res = OCRReportService.process_report(report.file.path)
            text = res.get('raw_text', '')
            return text[:8000] if text else "Unable to analyze report."
        except Exception as e:
            logger.warning(f"OCR text extraction failed for report {report.id}: {e}")
            return "Unable to analyze report."

    def _call_gemini(self, report, extracted_text, api_key):
        """
        Call Google Gemini API for medical report analysis.

        ⚠️ CONFIGURE: GEMINI_API_KEY in .env
        Free tier: 60 requests/minute at https://aistudio.google.com/
        """
        import requests as req_lib
        import base64

        model = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'

        DISCLAIMER = (
            '\n\n⚠️ DISCLAIMER: This is an AI-generated analysis for informational purposes only. '
            'It does NOT constitute medical advice or diagnosis. '
            'Always consult a qualified healthcare professional for medical decisions.'
        )

        SYSTEM_PROMPT = """You are a medical report reading assistant. Analyze this medical report and provide:

1. SUMMARY: A brief, clear summary of the key findings in simple language (2-3 sentences).
2. FINDINGS: List specific values/results. Mark each as NORMAL ✅ or ABNORMAL ⚠️. Include the reference range if visible.
3. RECOMMENDATION: Suggest which type of specialist to consult if needed, or what follow-up is appropriate. NEVER provide diagnosis. NEVER recommend specific medications.

Format your response EXACTLY as:
SUMMARY: [summary here]
FINDINGS: [findings here with normal/abnormal markers]
RECOMMENDATION: [recommendations here]

Keep language simple enough for a non-medical person to understand. If you cannot extract meaningful medical data, say so clearly."""

        try:
            if extracted_text == '[IMAGE_FILE]' or (not extracted_text and report.is_image):
                # Vision API for images
                with open(report.file.path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()

                ext = report.file_extension
                mime_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}
                mime = mime_map.get(ext, 'image/jpeg')

                payload = {
                    'contents': [{
                        'parts': [
                            {'text': SYSTEM_PROMPT},
                            {
                                'inline_data': {
                                    'mime_type': mime,
                                    'data': image_data
                                }
                            }
                        ]
                    }]
                }
            elif extracted_text:
                payload = {
                    'contents': [{
                        'parts': [{
                            'text': f'{SYSTEM_PROMPT}\n\nMEDICAL REPORT TEXT:\n{extracted_text}'
                        }]
                    }]
                }
            else:
                return {'summary': '', 'findings': '', 'recommendation': ''}

            response = req_lib.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Parse the response
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            result = self._parse_ai_response(raw_text)

            # Append disclaimer to all fields
            if result.get('summary'):
                result['summary'] += DISCLAIMER
            if result.get('recommendation'):
                result['recommendation'] += '\n\n⚠️ Always consult a qualified doctor before making any medical decisions.'

            return result

        except Exception as e:
            logger.error(f'Gemini API call failed: {e}')
            raise

    def _parse_ai_response(self, raw_text):
        """Parse structured AI response into fields."""
        result = {'summary': '', 'findings': '', 'recommendation': ''}

        lines = raw_text.split('\n')
        current_section = None
        buffer = []

        for line in lines:
            if line.startswith('SUMMARY:'):
                if current_section and buffer:
                    result[current_section] = '\n'.join(buffer).strip()
                current_section = 'summary'
                buffer = [line.replace('SUMMARY:', '').strip()]
            elif line.startswith('FINDINGS:'):
                if current_section and buffer:
                    result[current_section] = '\n'.join(buffer).strip()
                current_section = 'findings'
                buffer = [line.replace('FINDINGS:', '').strip()]
            elif line.startswith('RECOMMENDATION:'):
                if current_section and buffer:
                    result[current_section] = '\n'.join(buffer).strip()
                current_section = 'recommendation'
                buffer = [line.replace('RECOMMENDATION:', '').strip()]
            elif current_section:
                buffer.append(line)

        if current_section and buffer:
            result[current_section] = '\n'.join(buffer).strip()

        # If parsing failed, put full response in summary
        if not any(result.values()):
            result['summary'] = raw_text

        return result


class AskReportAIView(LoginRequiredMixin, View):
    """
    Per-report AI chat endpoint.
    Patient asks questions, AI responds based ONLY on the report context.
    Never provides diagnosis.

    ⚠️ CONFIGURE: GEMINI_API_KEY in .env
    """
    login_url = reverse_lazy('accounts:login')

    def post(self, request, pk, *args, **kwargs):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)
        question = request.POST.get('question', '').strip()

        if not question:
            return JsonResponse({'error': 'Please ask a question.'}, status=400)

        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key or api_key == 'YOUR_GEMINI_API_KEY':
            return JsonResponse({
                'answer': (
                    'AI is not configured yet. '
                    'Please add your GEMINI_API_KEY to the .env file '
                    'from https://aistudio.google.com/app/apikey to enable AI chat.'
                )
            })

        # Build context from extracted text or AI summary
        report_context = report.extracted_text or report.ai_summary or 'No report text available.'

        PROMPT = f"""You are a medical report explanation assistant. Answer the patient's question based ONLY on the provided report content.

IMPORTANT RULES:
- NEVER provide a diagnosis
- NEVER recommend specific medications  
- NEVER make predictions about health outcomes
- If the answer is not in the report, say so clearly
- Explain medical terms in simple language
- Always add a disclaimer to consult a doctor

REPORT CONTENT:
{report_context[:4000]}

PATIENT QUESTION: {question}

Provide a helpful, clear answer in simple language. End with a reminder to consult their doctor."""

        try:
            import requests as req_lib
            model = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'

            payload = {
                'contents': [{'parts': [{'text': PROMPT}]}]
            }
            response = req_lib.post(url, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            answer = data['candidates'][0]['content']['parts'][0]['text']
            return JsonResponse({'answer': answer})
        except Exception as e:
            logger.error(f'AI chat failed: {e}')
            return JsonResponse({'answer': 'AI assistant is temporarily unavailable. Please try again later.'})


# ============================================================================
# Report Management
# ============================================================================

class DeleteReportView(LoginRequiredMixin, View):
    """Securely delete a patient's own medical report."""
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)
        title = report.title

        # Delete the actual file from storage
        try:
            if report.file and os.path.isfile(report.file.path):
                os.remove(report.file.path)
        except Exception as e:
            logger.warning(f'File deletion failed for report {pk}: {e}')

        report.delete()
        messages.success(request, f'Report "{title}" has been permanently deleted.')
        return redirect('appointment:report-center')


class DownloadReportView(LoginRequiredMixin, View):
    """Securely serve a patient's own report file for download."""
    login_url = reverse_lazy('accounts:login')

    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, *args, **kwargs):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)

        if not report.file:
            messages.error(request, 'File not found.')
            return redirect('appointment:report-center')

        try:
            with open(report.file.path, 'rb') as f:
                file_data = f.read()

            # Determine content type
            ext = report.file_extension
            content_type_map = {
                'pdf': 'application/pdf',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')

            response = HttpResponse(file_data, content_type=content_type)
            filename = os.path.basename(report.file.name)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            logger.error(f'File download failed for report {pk}: {e}')
            messages.error(request, 'Could not download file. Please try again.')
            return redirect('appointment:report-center')
