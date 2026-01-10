import pytesseract
import cv2
from pathlib import Path

# Set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def run_tesseract(image_path):
    """
    Fallback OCR using Tesseract.
    Returns same unified format: [{text, confidence}]
    NOTE: Tesseract does NOT provide confidence reliably.
    """
    if not Path(image_path).exists():
        return []

    img = cv2.imread(image_path)
    if img is None:
        return []

    # Hindi + English
    text = pytesseract.image_to_string(
        img,
        lang="hin+eng",
        config="--psm 6"
    ).strip()

    if not text:
        return []

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Tesseract confidence is not reliable → assign neutral confidence
    return [
        {"text": line, "confidence": 0.50}
        for line in lines
    ]
