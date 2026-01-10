"""
Semantic Embedding Utilities
Uses CPU-friendly sentence-transformers for text embeddings
"""
from sentence_transformers import SentenceTransformer
import numpy as np

# Initialize model once (CPU-friendly)
model = None

def get_model():
    """Lazy load the model to avoid startup delays"""
    global model
    if model is None:
        print("Loading sentence embedding model (all-MiniLM-L6-v2)...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✓ Model loaded successfully")
    return model

def embed_text(text: str) -> list:
    """
    Generate semantic embedding for text.
    
    Args:
        text: Input text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    if not text or not text.strip():
        return None
    
    model = get_model()
    embedding = model.encode(text.strip())
    return embedding.tolist()

def batch_embed_texts(texts: list) -> list:
    """
    Generate embeddings for multiple texts efficiently.
    
    Args:
        texts: List of text strings
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = get_model()
    embeddings = model.encode(texts)
    return [emb.tolist() for emb in embeddings]
