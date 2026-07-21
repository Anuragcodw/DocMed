"""
OCR and AI Report Analyzer Service.
Provides robust text extraction for PDF, PNG, JPG, JPEG medical reports using:
- EasyOCR (Primary OCR)
- PyTesseract (Fallback OCR)
- PyPDF2 / pdf2image (PDF handling)
- OpenCV / Pillow (Image processing)

Cross-platform support:
- Windows Poppler path fallback: C:\\Users\\user\\Downloads\\Release-26.02.0-0\\poppler-26.02.0\\Library\\bin
- Windows Tesseract path fallback: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
- Linux / Production: Automatically detects system binaries via PATH / environment variables.
"""

import os
import sys
import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_WIN_POPPLER = r"C:\Users\user\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"
DEFAULT_WIN_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def get_poppler_path():
    """Return poppler path from environment variable or OS-specific fallback."""
    env_path = os.getenv("POPPLER_PATH")
    if env_path:
        return env_path
    if os.name == 'nt' and os.path.exists(DEFAULT_WIN_POPPLER):
        return DEFAULT_WIN_POPPLER
    return None


def get_tesseract_cmd():
    """Return tesseract command path from environment variable or OS-specific fallback."""
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd:
        return env_cmd
    if os.name == 'nt' and os.path.exists(DEFAULT_WIN_TESSERACT):
        return DEFAULT_WIN_TESSERACT
    return None


class OCRReportService:
    """
    Robust OCR Service for Medical Report Parsing with multi-level fallbacks.
    Guaranteed to never crash even if OCR dependencies or binaries are unavailable.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """Sanitizes raw extracted text."""
        if not text:
            return ""
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

    @classmethod
    def extract_from_image_easyocr(cls, file_path: str) -> str:
        """
        Primary OCR engine: EasyOCR.
        Catches all exceptions (ImportError, OSError DLL errors, CUDA/CPU errors).
        """
        try:
            import easyocr
            reader = easyocr.Reader(['en'], gpu=False)
            results = reader.readtext(file_path, detail=0)
            raw_text = " ".join(results)
            cleaned = cls.clean_text(raw_text)
            if cleaned:
                logger.info("Text successfully extracted via EasyOCR.")
                return cleaned
        except Exception as e:
            logger.warning(f"EasyOCR extraction unavailable/failed: {e}")
        return ""

    @classmethod
    def extract_from_image_tesseract(cls, file_path: str) -> str:
        """
        Fallback OCR engine: PyTesseract with OpenCV/Pillow preprocessing.
        """
        try:
            import pytesseract
            tesseract_cmd = get_tesseract_cmd()
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            # Preprocessing with OpenCV if available
            try:
                import cv2
                img = cv2.imread(file_path)
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                    raw_text = pytesseract.image_to_string(thresh)
                else:
                    from PIL import Image
                    img = Image.open(file_path)
                    raw_text = pytesseract.image_to_string(img)
            except Exception:
                from PIL import Image
                img = Image.open(file_path)
                raw_text = pytesseract.image_to_string(img)

            cleaned = cls.clean_text(raw_text)
            if cleaned:
                logger.info("Text successfully extracted via PyTesseract.")
                return cleaned
        except Exception as e:
            logger.warning(f"PyTesseract extraction unavailable/failed: {e}")
        return ""

    @classmethod
    def extract_from_pdf(cls, file_path: str) -> str:
        """
        Extracts text from PDF files:
        1. Attempts PyPDF2 direct text extraction.
        2. Converts PDF pages to images via pdf2image and runs OCR pipeline (EasyOCR -> PyTesseract).
        """
        extracted_text = ""

        # Step 1: Direct text extraction using PyPDF2
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_runs = []
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        text_runs.append(txt)
                extracted_text = cls.clean_text("\n".join(text_runs))
        except Exception as e:
            logger.warning(f"PyPDF2 direct extraction failed: {e}")

        if extracted_text:
            return extracted_text

        # Step 2: Convert PDF to images using pdf2image and run image OCR
        try:
            from pdf2image import convert_from_path
            poppler_path = get_poppler_path()
            if poppler_path:
                images = convert_from_path(file_path, poppler_path=poppler_path)
            else:
                images = convert_from_path(file_path)

            page_texts = []
            for i, image in enumerate(images):
                temp_img_path = f"{file_path}_temp_page_{i}.png"
                image.save(temp_img_path, 'PNG')
                try:
                    txt = cls.extract_from_image_easyocr(temp_img_path)
                    if not txt:
                        txt = cls.extract_from_image_tesseract(temp_img_path)
                    if txt:
                        page_texts.append(txt)
                finally:
                    if os.path.exists(temp_img_path):
                        try:
                            os.remove(temp_img_path)
                        except Exception:
                            pass

            extracted_text = cls.clean_text("\n".join(page_texts))
        except Exception as e:
            logger.warning(f"pdf2image OCR extraction failed: {e}")

        return extracted_text

    @classmethod
    def process_report(cls, file_path: str) -> dict:
        """
        Main entry point for processing medical report files (PDF, PNG, JPG, JPEG).
        Returns a dictionary with raw_text, structured data, and ai_summary.
        Guaranteed to never crash — returns "Unable to analyze report." on failure.
        """
        if not file_path or not os.path.exists(file_path):
            return {
                "raw_text": "Unable to analyze report.",
                "structured": {"error": "File does not exist"},
                "ai_summary": "Unable to analyze report."
            }

        ext = file_path.split('.')[-1].lower()
        extracted_text = ""

        try:
            if ext == 'pdf':
                extracted_text = cls.extract_from_pdf(file_path)
            elif ext in ['png', 'jpg', 'jpeg']:
                # EasyOCR -> Tesseract fallback pipeline
                extracted_text = cls.extract_from_image_easyocr(file_path)
                if not extracted_text:
                    extracted_text = cls.extract_from_image_tesseract(file_path)
            else:
                extracted_text = "Unsupported file format."
        except Exception as e:
            logger.error(f"OCR processing failed for {file_path}: {e}")
            extracted_text = ""

        if not extracted_text:
            extracted_text = "Unable to analyze report."

        structured = cls.structure_report(extracted_text)
        ai_summary = cls.generate_ai_summary_placeholder(structured, extracted_text)

        return {
            "raw_text": extracted_text,
            "structured": structured,
            "ai_summary": ai_summary
        }

    @staticmethod
    def structure_report(cleaned_text: str) -> dict:
        """Parses medical report text into structured metadata."""
        structured_data = {
            "patient_name": "Unknown",
            "date": "Unknown",
            "laboratory": "Unknown",
            "tests": []
        }
        if not cleaned_text or cleaned_text == "Unable to analyze report.":
            return structured_data

        name_match = re.search(r'(?:Patient Name|Name)\s*:\s*([^\n]+)', cleaned_text, re.IGNORECASE)
        if name_match:
            structured_data["patient_name"] = name_match.group(1).strip()

        date_match = re.search(r'(?:Date|Collected|Reported)\s*:\s*([^\n]+)', cleaned_text, re.IGNORECASE)
        if date_match:
            structured_data["date"] = date_match.group(1).strip()

        return structured_data

    @staticmethod
    def generate_ai_summary_placeholder(structured_data: dict, extracted_text: str) -> str:
        """Generates structured clinical summary."""
        if extracted_text == "Unable to analyze report.":
            return "Unable to analyze report."

        return (
            f"DocMed Medical Report Summary:\n"
            f"- Patient: {structured_data.get('patient_name')}\n"
            f"- Date: {structured_data.get('date')}\n"
            f"- Summary: {extracted_text[:300]}..."
        )
