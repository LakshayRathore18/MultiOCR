"""
Image hashing utilities for document identity
"""
import hashlib

def compute_image_hash(image_bytes):
    """
    Compute SHA256 hash of image bytes.
    This creates a unique fingerprint for each image.
    
    Args:
        image_bytes: Raw bytes of the image file
        
    Returns:
        str: Hexadecimal hash string (64 characters)
    """
    return hashlib.sha256(image_bytes).hexdigest()

def compute_image_hash_from_file(filepath):
    """
    Compute SHA256 hash directly from file path.
    
    Args:
        filepath: Path to image file
        
    Returns:
        str: Hexadecimal hash string (64 characters)
    """
    with open(filepath, 'rb') as f:
        image_bytes = f.read()
    return compute_image_hash(image_bytes)
