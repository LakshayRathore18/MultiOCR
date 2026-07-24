"""
Semantic Similarity Search
Find similar documents based on word-level similarity
"""
import numpy as np
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

def find_similar_documents(current_text: str = None, current_embedding: list = None, current_doc_id: int = None, threshold: float = 0.3, limit: int = 5, use_embeddings: bool = True):
    """
    Find similar documents based on cosine similarity of text embeddings (SentenceTransformer)
    with a fallback to word-level Jaccard similarity.
    
    Args:
        current_text: Text of current document
        current_embedding: Embedding vector of current document
        current_doc_id: ID of current document (to exclude from results)
        threshold: Minimum similarity score (0.0 to 1.0)
        limit: Maximum number of results to return
        use_embeddings: If True, attempts to use vector similarity
        
    Returns:
        List of similar documents with metadata
    """
    if not current_text:
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
    
    # Fetch all documents with text (exclude current document)
    if current_doc_id:
        cur.execute("""
            SELECT id, corrected_text, ocr_text, image_path, cer, status, version, text_embedding
            FROM documents
            WHERE id != %s
            ORDER BY updated_at DESC
            LIMIT 100
        """, (current_doc_id,))
    else:
        cur.execute("""
            SELECT id, corrected_text, ocr_text, image_path, cer, status, version, text_embedding
            FROM documents
            ORDER BY updated_at DESC
            LIMIT 100
        """)
    
    rows = cur.fetchall()
    conn.close()
    
    matches = []
    for row in rows:
        doc_id, corrected_text, ocr_text, image_path, cer, status, version, text_embedding = row
        
        # Prefer corrected text over OCR text
        compare_text = corrected_text if corrected_text else ocr_text
        
        if not compare_text:
            continue
        
        score = 0.0
        used_embedding = False
        
        if use_embeddings and current_embedding and text_embedding:
            try:
                # Handle potential JSON formats of text_embedding
                if isinstance(text_embedding, str):
                    import json
                    db_emb = json.loads(text_embedding)
                else:
                    db_emb = text_embedding
                
                if isinstance(db_emb, list) and len(db_emb) > 0:
                    score = cosine_similarity(current_embedding, db_emb)
                    used_embedding = True
            except Exception as e:
                print(f"⚠️ Error calculating cosine similarity for doc_id {doc_id}: {e}")
        
        if not used_embedding:
            # Fallback to word-level Jaccard similarity
            score = word_similarity(current_text, compare_text)
        
        if score >= threshold:
            matches.append({
                "doc_id": doc_id,
                "score": round(score, 3),
                "text": compare_text[:500] if compare_text else "",  # Preview only
                "full_text": compare_text,
                "image_path": image_path,
                "cer": round(cer, 4) if cer else None,
                "status": status,
                "version": version,
                "has_correction": corrected_text is not None,
                "similarity_method": "cosine" if used_embedding else "jaccard"
            })
    
    # Sort by similarity score (highest first)
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    return matches[:limit]
