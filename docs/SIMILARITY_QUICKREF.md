# 🚀 Quick Reference - Semantic Similarity

## Install (One Command)

```bash
pip install sentence-transformers
```

## How It Works

```
Document with corrected text exists
           ↓
User uploads similar image (cropped/retake)
           ↓
System computes semantic similarity
           ↓
Shows related documents as REFERENCE
           ↓
User can copy corrected text
```

## UI Location

**Review Page → Scroll Down → "Similar Documents (Reference Only)"**

## What You'll See

```
🔍 Similar Documents (Reference Only)

┌────────────────────────────────┐
│ 📄 Document #42  92% match    │
│ ✓ CORRECTED  •  CER: 0.05     │
│ [Preview text...]              │
│ [📋 Copy Text]  [👁️ View]     │
└────────────────────────────────┘
```

## Key Features

✅ Shows documents with 85%+ similarity  
✅ Prioritizes corrected text over OCR  
✅ One-click copy reference text  
✅ View similar document in new tab  
✅ Reduces duplicate correction work  

## Important

❌ Does NOT auto-link documents  
❌ Does NOT auto-replace text  
✅ Reference only - user decides  

## Test It

1. Upload manuscript → correct text
2. Upload cropped/retaken version
3. Go to review page
4. Look for "Similar Documents" panel

## Troubleshooting

**No similar docs showing?**
- Check if previous docs have corrections
- Threshold is 85% (very strict)
- Need at least 2 documents with embeddings

**Import error?**
```bash
pip install sentence-transformers
```

**Model download slow?**
- First run downloads 80MB model
- Subsequent runs use cached model
- No internet needed after first run

## Configuration

**Change similarity threshold:**

Edit `similarity/search.py` line 25:
```python
def find_similar_documents(..., threshold=0.85, ...):
    #                                    ↑
    #                        Change this (0.0 to 1.0)
```

**Values:**
- `0.90` = Very strict (near-duplicates only)
- `0.85` = Balanced (default)
- `0.75` = Relaxed (more suggestions)

## Architecture

```
┌──────────────────┐
│  Upload Image    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────┐
│   Run OCR        │────→│  Embedding   │
└──────────────────┘     └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  Store in DB │
                         └──────┬───────┘
                                │
         ┌──────────────────────┘
         │
         ▼
┌──────────────────┐
│ Human Correction │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────┐
│ Better Embedding │────→│  Update DB   │
└──────────────────┘     └──────────────┘
```

## Files

**Core:**
- `similarity/embeddings.py` - Embedding generation
- `similarity/search.py` - Similarity search

**Docs:**
- `SIMILARITY_GUIDE.md` - Complete guide
- `SIMILARITY_COMPLETE.md` - Implementation summary

## Status

✅ Database migrated  
✅ Code implemented  
✅ UI added  
✅ Docs complete  

**Ready to use!**

---

For full documentation: [SIMILARITY_GUIDE.md](SIMILARITY_GUIDE.md)
