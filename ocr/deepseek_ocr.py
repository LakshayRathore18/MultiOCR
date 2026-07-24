"""
DeepSeek OCR Engine for text recognition from images.
Adapted for Multi-OCR pipeline integration.
"""
import os
import base64
import requests
import re
import io 
from PIL import Image
from typing import Optional

DEVANAGARI_REGEX = re.compile(r"[^\u0900-\u097F\s।]+")

def strip_non_devanagari(text):
    """Remove non-Devanagari characters from text"""
    if not text:
        return ""
    return DEVANAGARI_REGEX.sub("", text)


class DeepSeekEngine:
    """OCR engine using DeepSeek local API for text recognition."""
    
    def __init__(self, api_url: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize DeepSeek OCR engine.
        
        Args:
            api_url: API endpoint URL (defaults to DEEPSEEK_API_URL env var or http://localhost:11434/api/chat)
            model: Model name to use (defaults to DEEPSEEK_MODEL env var or deepseek-ocr)
        """
        self.api_url = api_url or os.getenv("DEEPSEEK_API_URL", "http://localhost:11434/api/chat")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-ocr")
        
        if not self.api_url:
            raise ValueError("DeepSeek API URL not provided. Set DEEPSEEK_API_URL environment variable or pass api_url parameter.")
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 string with preprocessing.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        img = Image.open(image_path).convert("RGB")

        # FORCE minimum resolution
        w, h = img.size
        if w < 1600:
            scale = 1600 / w
            img = img.resize((1600, int(h * scale)), Image.BICUBIC)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=False)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    def recognize_text(self, image_path: str, language: str = "Devanagari") -> str:
        """
        Recognize text from an image using DeepSeek API.
        
        Args:
            image_path: Path to the image file
            language: Target language for OCR (default: Devanagari)
            
        Returns:
            Recognized text from the image
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            requests.RequestException: If API request fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Encode image
        base64_image = self._encode_image(image_path)
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Determine if we should use /api/generate or /api/chat
        is_chat = "/api/chat" in self.api_url
        
        if is_chat:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Read the text in this image.",
                        "images": [base64_image]
                    }
                ],
                "stream": False
            }
        else:
            payload = {
                "model": self.model,
                "prompt": "Read the text in this image.",
                "images": [base64_image],
                "stream": False
            }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            if is_chat:
                text = result.get("message", {}).get("content", "")
            else:
                text = result.get("response", "")
                
            # Fallback: if chat returned empty text or special tokens (like <|im_end|>), 
            # try running /api/generate as fallback!
            if is_chat and (not text.strip() or "<|im_end|>" in text or text.strip() == "<|im_end|>"):
                print("⚠️  DeepSeek chat endpoint returned empty/invalid response. Attempting generate fallback...")
                fallback_url = self.api_url.replace("/api/chat", "/api/generate")
                fallback_payload = {
                    "model": self.model,
                    "prompt": "Read the text in this image.",
                    "images": [base64_image],
                    "stream": False
                }
                fallback_resp = requests.post(fallback_url, headers=headers, json=fallback_payload, timeout=120)
                fallback_resp.raise_for_status()
                fallback_result = fallback_resp.json()
                text = fallback_result.get("response", "")
                
            return text.strip()
            
        except Exception as e:
            # If the chat request itself failed (e.g. 500 error), try generate fallback
            if is_chat:
                try:
                    print(f"⚠️  DeepSeek chat failed ({e}). Attempting generate fallback...")
                    fallback_url = self.api_url.replace("/api/chat", "/api/generate")
                    fallback_payload = {
                        "model": self.model,
                        "prompt": "Read the text in this image.",
                        "images": [base64_image],
                        "stream": False
                    }
                    fallback_resp = requests.post(fallback_url, headers=headers, json=fallback_payload, timeout=120)
                    fallback_resp.raise_for_status()
                    fallback_result = fallback_resp.json()
                    return fallback_result.get("response", "").strip()
                except Exception as fallback_err:
                    print(f"❌ Both chat and generate failed. Fallback error: {fallback_err}")
            raise e


def init_deepseek_model():
    """Initialize DeepSeek OCR model once (for reuse)"""
    try:
        engine = DeepSeekEngine()
        print(f"✓ DeepSeek configured: {engine.api_url} (model: {engine.model})")
        return engine
    except Exception as e:
        print(f"⚠️  Warning: DeepSeek not configured: {e}")
        return None


def run_deepseek(image_path, model=None):
    """
    Run DeepSeek OCR and return standardized results.
    
    Args:
        image_path: Path to the image file
        model: Pre-initialized DeepSeekEngine instance
        
    Returns:
        List of dicts with 'text' and 'confidence' (confidence is set to 0.9 as DeepSeek doesn't provide it)
    """
    if model is None:
        model = init_deepseek_model()
        if model is None:
            return []
    
    try:
        # Get raw text from DeepSeek
        raw_text = model.recognize_text(image_path)
        print(f"DeepSeek raw output length: {len(raw_text)}")
        if raw_text:
            print(f"DeepSeek raw output: {raw_text[:200]}...")
        
        # If empty response, return empty list
        if not raw_text or not raw_text.strip():
            print("⚠️  DeepSeek returned empty response")
            return []
        
        # Try to clean to Devanagari only
        cleaned_text = strip_non_devanagari(raw_text)
        
        # Check if cleaned text has meaningful content (not just punctuation)
        # Count actual Devanagari letters (not just danda/punctuation)
        if cleaned_text.strip():
            # Remove common punctuation to check if actual letters remain
            test_text = cleaned_text.replace('।', '').replace('॥', '').replace(' ', '').replace('\n', '')
            if len(test_text) < 5:  # Less than 5 actual characters = filtering was too aggressive
                print("⚠️  Devanagari filtering removed meaningful text (only punctuation left), using raw output")
                cleaned_text = raw_text.strip()
        else:
            print("⚠️  No Devanagari text found, using raw output")
            cleaned_text = raw_text.strip()
        
        # Split into lines and return standardized format
        lines = cleaned_text.strip().split('\n')
        output = []
        
        for line in lines:
            line = line.strip()
            if line:
                output.append({
                    "text": line,
                    "confidence": 0.9  # DeepSeek doesn't provide confidence, use high default
                })
        
        print(f"DeepSeek extracted {len(output)} lines")
        return output
    
    except Exception as e:
        print(f"⚠️  DeepSeek OCR error: {e}")
        import traceback
        traceback.print_exc()
        return []
