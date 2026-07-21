"""
DocMed ML Utilities and Helper tools.
Includes model saving/loading routines, logging configurations,
and evaluation metrics calculation.
"""

import os
import logging
import joblib

logger = logging.getLogger(__name__)

def save_model(model, filepath: str) -> bool:
    """
    Saves a trained model to disk using joblib.
    """
    try:
        dir_name = os.path.dirname(filepath)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        joblib.dump(model, filepath)
        logger.info(f"Model saved successfully to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save model to {filepath}: {e}")
        return False


def load_model(filepath: str):
    """
    Loads a saved model from disk.
    """
    if os.path.exists(filepath):
        try:
            return joblib.load(filepath)
        except Exception as e:
            logger.error(f"Failed to load model from {filepath}: {e}")
    return None


def calculate_metrics(y_true, y_pred) -> dict:
    """
    Calculates precision, recall, f1, and accuracy scores for ML validation.
    """
    try:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted')),
            "recall": float(recall_score(y_true, y_pred, average='weighted')),
            "f1_score": float(f1_score(y_true, y_pred, average='weighted'))
        }
    except ImportError:
        logger.warning("scikit-learn is not installed. Returning empty metrics dict.")
        return {}
