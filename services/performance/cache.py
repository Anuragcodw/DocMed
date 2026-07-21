import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class PerformanceService:
    @staticmethod
    def get_cached_data(key: str):
        """Retrieves data from Django cache (Redis/InMemory)."""
        data = cache.get(key)
        if data:
            logger.info(f"Cache hit for key: {key}")
        else:
            logger.info(f"Cache miss for key: {key}")
        return data

    @staticmethod
    def set_cached_data(key: str, value, timeout: int = 300):
        """Saves data into Django cache with timeout."""
        cache.set(key, value, timeout)
        logger.info(f"Cached key: {key} for {timeout}s")

    @staticmethod
    def invalidate_cache(key: str):
        """Removes key from cache."""
        cache.delete(key)
        logger.info(f"Invalidated cache key: {key}")


# Celery Tasks Placeholders
# Developers can import and run tasks asynchronously using:
# run_ocr_task.delay(report_id)

def celery_task(func):
    """Decorator to mark functions as Celery tasks in the architecture."""
    def delay(*args, **kwargs):
        logger.info(f"[Celery Task Triggered Asynchronously] Running {func.__name__} in background worker.")
        return func(*args, **kwargs)
    func.delay = delay
    return func

@celery_task
def run_ocr_task(report_id: int):
    """Asynchronous worker task to perform report OCR and extraction."""
    from ai.services.report_analyzer import ReportAnalyzerService
    from appointment.models import MedicalReport, ExtractedText, AIAnalysis
    try:
        report = MedicalReport.objects.get(id=report_id)
        report.status = 'processing'
        report.save()

        analyzer = ReportAnalyzerService()
        result = analyzer.extract_text(report.file.path)
        
        # Save OCR raw text
        ExtractedText.objects.update_or_create(
            report=report,
            defaults={'raw_text': result['text'], 'confidence': result['confidence'], 'ocr_engine': result['engine']}
        )
        
        # Run AI analysis
        analysis_data = analyzer.analyze_report(result['text'])
        AIAnalysis.objects.update_or_create(
            report=report,
            defaults={
                'detected_diseases': analysis_data['detected_diseases'],
                'possible_diseases': analysis_data['possible_diseases'],
                'confidence_score': analysis_data['confidence_score'],
                'abnormal_values': analysis_data['abnormal_values'],
                'normal_values': analysis_data['normal_values'],
                'critical_values': analysis_data['critical_values'],
                'possible_causes': analysis_data['possible_causes'],
                'lifestyle_advice': analysis_data['lifestyle_advice'],
                'food_advice': analysis_data['food_advice'],
                'exercise_advice': analysis_data['exercise_advice'],
                'next_steps': analysis_data['next_steps'],
                'recommended_specialist': analysis_data['recommended_specialist'],
                'emergency_warning': analysis_data['emergency_warning']
            }
        )

        # Run ML prediction pipeline models
        from ml.prediction_pipeline.base import MLPredictionEngine
        from appointment.models import Prediction
        # Mock patient feature values (e.g. age, glucose, cholesterol, BP, weight/height)
        features = {
            'age': 45.0,
            'glucose': 140.0,
            'bmi': 28.2,
            'bp': 135.0,
            'insulin': 85.0,
            'cholesterol': 250.0,
            'systolic': 135.0,
            'diastolic': 85.0,
            'weight': 86.0,
            'height': 1.75
        }
        ml_results = MLPredictionEngine.run_all(features)
        for ml in ml_results:
            Prediction.objects.create(
                patient=report.patient,
                report=report,
                prediction_type=ml['prediction_type'],
                result=ml['result'],
                probability=ml['probability'],
                risk_score=ml['risk_score'],
                lifestyle_suggestions=ml['lifestyle_suggestions']
            )

        report.status = 'completed'
        report.save()
        logger.info(f"OCR and AI Analysis completed for report {report_id}")
    except Exception as e:
        logger.error(f"OCR background task failed for report {report_id}: {e}")
        if 'report' in locals():
            report.status = 'failed'
            report.save()
