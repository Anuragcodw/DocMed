"""
services/gemini_service.py
Re-usable bridge for Gemini AI generation services.
"""
from ai.services.gemini import generate_response, GeminiClient

# Cached singleton client instance to avoid repeated initialization
_gemini_client = GeminiClient()

def generate_ai_response(message: str) -> str:
    """
    Generate AI response using Gemini Flash model.
    Initializes model only once via GeminiClient singleton.
    """
    return _gemini_client.generate_content(prompt=message)

__all__ = ['generate_ai_response', 'generate_response', 'GeminiClient']
