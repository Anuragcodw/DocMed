"""
Base predictor abstraction for DocMed ML pipeline.

All future ML predictors should subclass BasePredictor and implement
the load_model() and predict() methods.

Example:
    class SymptomPredictor(BasePredictor):
        def load_model(self):
            self.model = joblib.load('symptom_model.pkl')

        def predict(self, input_data):
            return self.model.predict(input_data)
"""

import abc
import logging

logger = logging.getLogger(__name__)


class BasePredictor(abc.ABC):
    """
    Abstract base class for all DocMed ML predictors.

    Subclasses must implement:
      - load_model():  Load the trained model from disk or remote.
      - predict(input_data): Run inference and return results.
    """

    def __init__(self):
        self._model = None
        self._is_loaded = False

    @abc.abstractmethod
    def load_model(self):
        """Load the trained model. Called once at initialization."""
        raise NotImplementedError

    @abc.abstractmethod
    def predict(self, input_data):
        """
        Run inference on input_data.

        Args:
            input_data: The preprocessed input (format depends on predictor).

        Returns:
            Prediction result (format depends on predictor).
        """
        raise NotImplementedError

    def ensure_loaded(self):
        """Lazy-load the model on first prediction call."""
        if not self._is_loaded:
            try:
                self.load_model()
                self._is_loaded = True
                logger.info(f'{self.__class__.__name__} model loaded successfully.')
            except Exception as e:
                logger.error(f'Failed to load {self.__class__.__name__}: {e}')
                raise

    def safe_predict(self, input_data):
        """
        Predict with error handling.
        Returns None on failure instead of raising.
        """
        try:
            self.ensure_loaded()
            return self.predict(input_data)
        except Exception as e:
            logger.error(f'{self.__class__.__name__}.predict() failed: {e}')
            return None
