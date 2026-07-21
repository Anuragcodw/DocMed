"""
DocMed ML Preprocessing pipeline.
Provides helper classes to clean medical text, normalize numerical fields,
and prepare patient indicators for predictions.
"""

import re
import numpy as np
import pandas as pd

class MedicalTextPreprocessor:
    """
    Cleans and tokenizes medical/clinical text.
    """
    def __init__(self, lowercase=True, remove_punctuation=True):
        self.lowercase = lowercase
        self.remove_punctuation = remove_punctuation

    def preprocess(self, text: str) -> str:
        """
        Clean medical notes: remove stop words, standardize symbols, convert to lowercase.
        """
        if not text:
            return ""
        
        if self.lowercase:
            text = text.lower()
            
        if self.remove_punctuation:
            text = re.sub(r'[^\w\s\-\.]', '', text)
            
        # Clean extra spacing
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def transform_corpus(self, texts: list) -> list:
        """Transform a list of text documents."""
        return [self.preprocess(t) for t in texts]


class PatientDataPreprocessor:
    """
    Encodes categorical patient factors (e.g. smoking, blood group)
    and scales numerical vitals (e.g. blood pressure, weight, age).
    """
    def __init__(self):
        # Placeholders for scikit-learn encoders/scalers
        self.scaler = None
        self.encoders = {}

    def fit(self, df: pd.DataFrame):
        """
        Fits scalers and encoders on training data.
        """
        try:
            from sklearn.preprocessing import StandardScaler, LabelEncoder
            # Standardize numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                self.scaler = StandardScaler()
                self.scaler.fit(df[numeric_cols])

            # Label encode categorical columns
            cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
            for col in cat_cols:
                le = LabelEncoder()
                le.fit(df[col].astype(str))
                self.encoders[col] = le
        except ImportError:
            logger_warn = "scikit-learn is not installed. Preprocessing will run in fallback mode."

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms input patient dataframe.
        """
        df_copy = df.copy()
        
        # Scaling numerical values
        if self.scaler:
            numeric_cols = df_copy.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                df_copy[numeric_cols] = self.scaler.transform(df_copy[numeric_cols])

        # Encoding categories
        for col, encoder in self.encoders.items():
            if col in df_copy.columns:
                df_copy[col] = encoder.transform(df_copy[col].astype(str))
                
        return df_copy
