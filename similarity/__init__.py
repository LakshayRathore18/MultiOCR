"""
Similarity module initialization
"""
from .embeddings import embed_text, batch_embed_texts
from .search import find_similar_documents, cosine_similarity

__all__ = ['embed_text', 'batch_embed_texts', 'find_similar_documents', 'cosine_similarity']
