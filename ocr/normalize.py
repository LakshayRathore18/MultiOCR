import re
from ocr.devanagari_unicode import (
    clean_devanagari_text,
    analyze_text_quality,
    is_devanagari
)

def normalize_text(text):
    """
    Normalize text by:
    1. Cleaning Devanagari Unicode sequences (matra correction)
    2. Removing extra whitespace
    """
    if not text:
        return text
    
    # Check if text contains Devanagari
    has_devanagari = any(is_devanagari(ch) for ch in text)
    
    if has_devanagari:
        # Apply Devanagari-specific cleaning
        text = clean_devanagari_text(text)
    
    # Standard normalization
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    
    return text

def validate_ocr_text(text):
    """
    Validate OCR output quality for Devanagari text.
    Returns quality metrics.
    """
    return analyze_text_quality(text)
