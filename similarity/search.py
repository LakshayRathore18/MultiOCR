"""
Semantic Similarity Search
Compare a raw OCR query with both original and corrected document text.
"""
import numpy as np
import json
import re
from database.db import get_db

def cosine_similarity(a: list, b: list) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        a, b: Embedding vectors (lists of floats)
        
    Returns:
        Similarity score between 0 and 1
    """
    a = np.array(a)
    b = np.array(b)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))

def word_similarity(text1: str, text2: str) -> float:
    """
    Compute word-level similarity between two texts using Jaccard similarity.
    
    Args:
        text1, text2: Input texts to compare
        
    Returns:
        Similarity score between 0 and 1 based on word overlap
    """
    if not text1 or not text2:
        return 0.0
    
    # Tokenize into words (split on whitespace and Devanagari punctuation)
    # Remove empty strings and convert to lowercase
    words1 = set(re.split(r'[\s\u0964\u0965]+', text1.lower().strip()))
    words2 = set(re.split(r'[\s\u0964\u0965]+', text2.lower().strip()))
    
    # Remove empty strings
    words1.discard('')
    words2.discard('')
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity: intersection / union
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    if union == 0:
        return 0.0
    
    return intersection / union

def _embedding_score(query, stored):
    """Return no score for missing, malformed, or incompatible vectors."""
    if query is None or stored is None:
        return None
    try:
        stored = json.loads(stored) if isinstance(stored, str) else stored
        a = np.asarray(query, dtype=float)
        b = np.asarray(stored, dtype=float)
        if (a.ndim != 1 or a.size == 0 or a.shape != b.shape
                or not np.isfinite(a).all() or not np.isfinite(b).all()
                or np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0):
            return None
        score = cosine_similarity(a, b)
        return float(np.clip(score, -1.0, 1.0)) if np.isfinite(score) else None
    except (TypeError, ValueError, OverflowError):
        return None


def find_similar_documents(current_text: str = None, current_embedding: list = None, current_doc_id: int = None, threshold: float = 0.3, limit: int = 5, use_embeddings: bool = True):
    """
    Rank each document by its stronger raw-OCR/corrected cosine match.
    Use the stronger Jaccard match only if neither vector can be compared.
    Both texts are returned together, regardless of which source matched.
    
    Args:
        current_text: Original raw OCR text of current document
        current_embedding: Embedding vector of current document
        current_doc_id: ID of current document (to exclude from results)
        threshold: Minimum similarity score (0.0 to 1.0)
        limit: Maximum number of results to return
        use_embeddings: If True, attempts to use vector similarity
        
    Returns:
        List of similar documents with metadata
    """
    if not current_text or not current_text.strip() or limit <= 0:
        return []
        
    # Generate query embedding if not provided and use_embeddings is True
    if current_embedding is None and use_embeddings:
        try:
            from similarity.embeddings import embed_text
            current_embedding = embed_text(current_text)
        except Exception as e:
            print(f"⚠️ Failed to generate embedding for similarity search: {e}")
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT id, corrected_text, ocr_text, image_path, cer, status, updated_at,
                   text_embedding, ocr_embedding
            FROM documents
        """
        params = ()
        if current_doc_id is not None:
            query += " WHERE id != %s"
            params = (current_doc_id,)
        query += " ORDER BY updated_at DESC, id DESC LIMIT 100"
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    
    matches = []
    for row in rows:
        (doc_id, corrected_text, ocr_text, image_path, cer, status, updated_at,
         text_embedding, ocr_embedding) = row
        
        # Prefer corrected text over OCR text
        has_correction = bool(corrected_text and corrected_text.strip())
        compare_text = corrected_text if has_correction else ocr_text
        
        if not compare_text:
            continue
        
        raw_score = corrected_score = None
        if use_embeddings:
            if ocr_text and ocr_text.strip():
                raw_score = _embedding_score(current_embedding, ocr_embedding)
            if has_correction:
                corrected_score = _embedding_score(current_embedding, text_embedding)

        scores = [("raw", raw_score), ("corrected", corrected_score)]
        valid_scores = [(source, score) for source, score in scores if score is not None]
        used_embedding = bool(valid_scores)
        if not valid_scores:
            raw_score = word_similarity(current_text, ocr_text) if ocr_text and ocr_text.strip() else None
            corrected_score = word_similarity(current_text, corrected_text) if has_correction else None
            valid_scores = [(source, score) for source, score in
                            [("raw", raw_score), ("corrected", corrected_score)]
                            if score is not None]
        if not valid_scores:
            continue
        # max preserves the first (raw) entry on exact ties.
        matched_on, score = max(valid_scores, key=lambda item: item[1])
        
        if score >= threshold:
            matches.append({
                "doc_id": doc_id,
                "score": round(score, 3),
                "ocr_text": ocr_text or "",
                "corrected_text": corrected_text if has_correction else None,
                "raw_score": round(raw_score, 3) if raw_score is not None else None,
                "corrected_score": round(corrected_score, 3) if corrected_score is not None else None,
                "matched_on": matched_on,
                "text": compare_text[:500] if compare_text else "",  # Preview only
                "full_text": compare_text,
                "image_path": image_path,
                "cer": round(cer, 4) if cer is not None else None,
                "status": status,
                "updated_at": updated_at.isoformat() if updated_at else None,
                "has_correction": has_correction,
                "similarity_method": "cosine" if used_embedding else "jaccard",
                "_rank_score": score,
            })
    
    # Sort by similarity score (highest first)
    matches.sort(key=lambda x: (-x["_rank_score"], x["doc_id"]))
    results = matches[:limit]
    for match in results:
        del match["_rank_score"]
    return results
