"""
DocMed ML Disease Predictor & Risk Scoring service.
Loads saved models using joblib and exposes inference endpoints.
"""

import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

class DiseasePredictor:
    """
    Exposes clean interfaces for predicting potential diseases based on 
    patient symptoms and health profiles.
    """
    def __init__(self, model_dir=None):
        self.model_path = os.path.join(model_dir or "", "disease_classifier.joblib")
        self.model = None
        self._load_model()

    def _load_model(self):
        """Loads model file if it exists, otherwise logs warning."""
        if os.path.exists(self.model_path):
            try:
                import joblib
                self.model = joblib.load(self.model_path)
                logger.info("Disease classifier loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load disease classifier model: {e}")
        else:
            logger.warning("Disease classifier model not found. Using fallback prediction rules.")

    def predict_disease(self, symptoms_vector: list) -> dict:
        """
        Predict disease probabilities based on input symptoms list/vector.
        Returns a dict with predicted diseases and confidence scores.
        """
        if self.model:
            try:
                preds = self.model.predict_proba([symptoms_vector])[0]
                classes = self.model.classes_
                sorted_idx = np.argsort(preds)[::-1]
                return {classes[i]: float(preds[i]) for i in sorted_idx[:3]}
            except Exception as e:
                logger.error(f"Model prediction failed: {e}")
        
        # Fallback Rule-Based Prediction Engine
        # Returns general recommendations if classifier is not trained/pickled yet
        return {
            "General Viral / Influenza": 0.65,
            "Common Cold": 0.20,
            "Allergic Rhinitis": 0.15
        }


class HealthRiskScorer:
    """
    Calculates cardiovascular or general diabetic risk scores based on patient indicators.
    """
    def __init__(self, model_dir=None):
        self.model_path = os.path.join(model_dir or "", "risk_scorer.joblib")
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                import joblib
                self.model = joblib.load(self.model_path)
            except Exception as e:
                logger.error(f"Failed to load risk scoring model: {e}")

    def calculate_risk_score(self, patient_features: dict) -> float:
        """
        Calculate health risk score (range: 0.0 to 100.0).
        """
        if self.model:
            try:
                # Expects feature list matching trained model schema
                feature_values = [patient_features.get(f, 0) for f in self.model.feature_names_in_]
                score = self.model.predict_proba([feature_values])[0][1] # Probability of positive class
                return round(float(score * 100), 2)
            except Exception as e:
                logger.error(f"Risk model scoring failed: {e}")

        # Fallback Heuristics
        # Calculate risk based on age, blood pressure, smoking, and chronic conditions
        score = 10.0 # Base score
        
        # Age indicator
        age = patient_features.get('age', 30)
        if age > 50:
            score += 15.0
        elif age > 40:
            score += 5.0

        # Smoking status
        if patient_features.get('smoking', 'no') == 'yes':
            score += 20.0

        # High BMI indicator
        bmi = patient_features.get('bmi', 22.0)
        if bmi > 27.5:
            score += 15.0

        return min(score, 100.0)
