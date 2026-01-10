# Semantic Similarity Feature - Setup Guide

## 📦 Required Package

This feature requires the `sentence-transformers` library for CPU-based semantic embeddings.

### Installation

**Windows (using pip):**
```bash
pip install sentence-transformers
```

**Or add to your requirements:**
```bash
pip install sentence-transformers numpy
```

### Model Download

The model `all-MiniLM-L6-v2` will be downloaded automatically on first use (~80MB).

- **CPU-friendly**: Optimized for CPU inference
- **Fast**: Processes text in milliseconds
- **Accurate**: Good semantic understanding for similarity

---

## 🧠 How It Works

### 1. Text Embedding Generation

When you save OCR results or corrections:
```python
# Embeddings are automatically generated
text → embed_text() → 384-dimensional vector → stored in DB
```

**Priority:**
- If `corrected_text` exists → embed that (better quality)
- Else → embed `ocr_text`

### 2. Similarity Search

When viewing a document on the review page:
```python
# System finds similar documents
current_embedding → find_similar_documents() → top 5 matches
```

**Threshold:** 85% similarity (configurable)

### 3. Database Storage

```sql
documents (
    ...
    text_embedding JSONB  -- Stores vector as JSON array
)
```

**Why JSONB?**
- CPU-friendly (no GPU needed)
- No pgvector dependency
- Easy to debug and inspect
- Can migrate to FAISS/Milvus later

---

## 🎯 Use Cases

### Case 1: Cropped Images
```
User uploads cropped version of manuscript
→ Image hash different (correct behavior)
→ Semantic search finds original document
→ Shows: "Similar document found with corrections"
→ User can reference the corrected text
```

### Case 2: Retake Photos
```
Same manuscript, different lighting/angle
→ Image hash different
→ Text content similar
→ System suggests: "Document #42 looks similar (92% match)"
→ User can copy corrections
```

### Case 3: Same Page, Different Scan
```
Another researcher scans same manuscript page
→ Different scan quality
→ Content semantically similar
→ Shows previous scholarly corrections
→ Reduces duplicate correction effort
```

---

## 🔧 Configuration

### Similarity Threshold

In `similarity/search.py`:
```python
def find_similar_documents(..., threshold=0.85, ...):
    # 0.85 = 85% similarity
    # Lower = more suggestions (but less relevant)
    # Higher = fewer suggestions (but more precise)
```

**Recommended:**
- `0.90+` → Very strict (only near-duplicates)
- `0.85` → Balanced (default)
- `0.75` → Relaxed (more suggestions)

### Result Limit

```python
find_similar_documents(..., limit=5):
    # Max 5 similar documents shown
```

---

## 📊 Performance

### CPU Usage
- **Embedding generation**: ~50-100ms per document
- **Similarity search**: ~10-30ms (100 documents)
- **Model size**: ~80MB RAM

### When Embeddings Are Generated

1. **On OCR save** → OCR text embedded
2. **On correction save** → Corrected text embedded (overwrites)
3. **On reprocess** → New OCR embedded

---

## 🎨 UI Behavior

### Review Page

**Similar Documents Panel** (appears if matches found):
```
🔍 Similar Documents (Reference Only)

┌─────────────────────────────────────┐
│ 📄 Document #42  ✓ CORRECTED  92% │
│ Version 2  •  CER: 0.0523          │
│                                     │
│ [Preview of corrected text...]      │
│                                     │
│ [📋 Copy Text]  [👁️ View]          │
└─────────────────────────────────────┘
```

**Features:**
- Shows match percentage
- Indicates if document was corrected
- Displays CER (if available)
- One-click copy text
- Open in new tab to view

---

## 🧪 Testing

### Test 1: Upload and Correct
```bash
1. Upload manuscript → OCR runs
2. Review page → Correct text → Save
3. Check: embedding stored in database
```

### Test 2: Upload Similar Image
```bash
1. Upload cropped/retaken version
2. Go to review page
3. Check: "Similar Documents" panel appears
4. Verify: Shows previously corrected document
```

### Test 3: Copy Reference
```bash
1. On review page with similar docs
2. Click "📋 Copy Text" on a similar doc
3. Paste into correction textarea
4. Adjust as needed → Save
```

---

## 🔍 Debugging

### Check if embeddings are stored:
```sql
SELECT id, 
       CASE 
           WHEN text_embedding IS NOT NULL THEN 'YES'
           ELSE 'NO'
       END as has_embedding,
       jsonb_array_length(text_embedding) as embedding_size
FROM documents
WHERE text_embedding IS NOT NULL
LIMIT 5;
```

### View similarity scores manually:
```python
from similarity import embed_text, cosine_similarity

text1 = "Your OCR text"
text2 = "Another document text"

emb1 = embed_text(text1)
emb2 = embed_text(text2)

score = cosine_similarity(emb1, emb2)
print(f"Similarity: {score:.3f}")
```

---

## ⚠️ Important Notes

### NOT Auto-Linking
- System does NOT automatically link documents
- It only shows SUGGESTIONS for reference
- User decides what to do with similar documents

### Privacy
- Embeddings are mathematical representations
- Cannot reverse-engineer original text from embeddings
- Safe for sensitive content

### Performance
- First run downloads model (~80MB)
- Subsequent runs use cached model
- No internet needed after initial download

---

## 🚀 Future Enhancements

### Phase 1 (Current)
- ✅ CPU-based embeddings
- ✅ JSONB storage
- ✅ Similarity search in Python

### Phase 2 (Future)
- Migrate to pgvector for faster search
- Add FAISS index for large datasets
- Implement batch embedding updates

### Phase 3 (Advanced)
- Perceptual image hashing (pHash)
- Visual similarity (not just text)
- Multi-modal embeddings (text + image)

---

## 📚 References

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
- Paper: https://arxiv.org/abs/1908.10084
- Hugging Face: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

**Why this model?**
- CPU-optimized
- 384 dimensions (lightweight)
- General-purpose semantic understanding
- Widely used in production

---

**Status:** ✅ Implemented & Ready
**CPU-Friendly:** ✅ Yes
**Dependencies:** sentence-transformers, numpy
**Database:** PostgreSQL with JSONB
