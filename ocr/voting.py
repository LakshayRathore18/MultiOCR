from ocr.normalize import normalize_text
from difflib import SequenceMatcher

def is_similar(text1, text2, threshold=0.85):
    """Check if two texts are similar using string similarity"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() > threshold

def is_duplicate(text, existing_texts, threshold=0.85):
    """Check if text is duplicate or very similar to existing texts"""
    text_lower = text.lower()
    
    for existing in existing_texts:
        existing_lower = existing.lower()
        
        # Check exact similarity
        if is_similar(text, existing, threshold):
            return True
        
        # Check if new text is substring of existing (partial duplicate)
        if text_lower in existing_lower:
            return True
        
        # Check if new text is just a small fragment of existing text
        if len(text) < len(existing) * 0.3 and text_lower in existing_lower:
            return True
    
    return False

def ocr_voting(paddle_results, deepseek_results=None, min_confidence=0.6):
    """
    Compare OCR results and select the one with higher confidence for each line.
    Supports comparison between Paddle and DeepSeek.
    Filters out duplicates and low confidence results.
    
    Special case: If all OCR engines detect the same number of lines,
    skip duplicate filtering to preserve all lines.
    
    Args:
        paddle_results: List of dicts with 'text' and 'confidence' from PaddleOCR
        deepseek_results: Optional list of dicts with 'text' and 'confidence' from DeepSeek
        min_confidence: Minimum confidence threshold (default 0.6)
    
    Returns:
        List of dicts with the best result for each line (deduplicated)
    """
    final_results = []
    seen_texts = []
    
    # Check if all engines detected same number of lines
    line_counts = [len(paddle_results)]
    if deepseek_results:
        line_counts.append(len(deepseek_results))
    
    same_line_count = len(set(line_counts)) == 1  # All counts are the same
    
    max_len = max(line_counts)
    
    for i in range(max_len):
        p = paddle_results[i] if i < len(paddle_results) else None
        d = deepseek_results[i] if deepseek_results and i < len(deepseek_results) else None
        
        # Normalize text
        if p:
            p["text"] = normalize_text(p["text"])
        if d:
            d["text"] = normalize_text(d["text"])
        
        # Vote based on confidence (Paddle vs DeepSeek)
        selected = None
        candidates = [x for x in [p, d] if x is not None]
        
        if candidates:
            # Select the one with highest confidence
            selected = max(candidates, key=lambda x: x["confidence"])
        
        # Apply filtering
        if selected and selected["confidence"] >= min_confidence:
            # If same line count, skip duplicate check - keep all lines
            if same_line_count:
                final_results.append(selected)
            else:
                # Different line counts - apply duplicate filtering
                if not is_duplicate(selected["text"], seen_texts):
                    final_results.append(selected)
                    seen_texts.append(selected["text"])
    
    return final_results
