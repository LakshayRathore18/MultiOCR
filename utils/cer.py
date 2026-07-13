import Levenshtein

def compute_cer(pred, gt):
    """
    Computes Character Error Rate (CER) between predicted and ground truth text.
    
    Args:
        pred (str): Predicted OCR text
        gt (str): Ground truth (actual) text
    
    Returns:
        float: CER value (0 = perfect match, higher = more errors)
        None: If ground truth is empty
    """
    if not gt:
        return None
    return Levenshtein.distance(pred, gt) / max(len(gt), 1)
