"""
DocMed ML Medical Report Classification.
Classifies medical documents and extracts key metrics from text findings.
"""

import os
import logging

logger = logging.getLogger(__name__)

class ReportClassifier:
    """
    Exposes clean interfaces to classify medical report types 
    (Blood test, MRI, CT Scan, X-Ray) based on extracted text contents.
    """
    def __init__(self, model_dir=None):
        self.model_path = os.path.join(model_dir or "", "report_classifier.joblib")
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                import joblib
                self.model = joblib.load(self.model_path)
            except Exception as e:
                logger.error(f"Failed to load report classifier: {e}")

    def classify_report(self, report_text: str) -> str:
        """
        Classifies medical reports based on keywords / extracted text contents.
        Returns one of: 'blood_test', 'mri', 'x_ray', 'ct_scan', 'other'.
        """
        if self.model:
            try:
                return self.model.predict([report_text])[0]
            except Exception as e:
                logger.error(f"Model report classification failed: {e}")

        # Fallback Keywords Search
        text_lower = report_text.lower()
        if "hemoglobin" in text_lower or "cbc" in text_lower or "cholesterol" in text_lower or "wbc" in text_lower:
            return "blood_test"
        elif "mri" in text_lower or "magnetic resonance" in text_lower:
            return "mri"
        elif "xray" in text_lower or "x-ray" in text_lower or "chest xray" in text_lower:
            return "x_ray"
        elif "ct scan" in text_lower or "computed tomography" in text_lower:
            return "ct_scan"
            
        return "other"
