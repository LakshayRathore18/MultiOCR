# Hash-Based Document Identity System

## 🎯 Overview

This implementation aligns the system with the project's core philosophy: **the image IS the document, not each upload attempt**. Using SHA256 hashing, the system now correctly identifies and tracks manuscripts across multiple upload attempts.

## 🔑 Key Architectural Changes

### 1. **Image Hashing**
Every uploaded image gets a unique SHA256 hash:
```python
image_hash = SHA256(image_bytes)
```

This hash serves as the document's **permanent identity**.

### 2. **Database Schema Updates**

New columns added to `documents` table:
- `image_hash` (TEXT): SHA256 fingerprint of the image
- `parent_id` (INTEGER): References the original document ID for version tracking
- Index on `image_hash` for fast lookups

Run migration:
```bash
python migrate_db.py
```

### 3. **Upsert Logic (Not Blind Insert)**

**Before (❌ Wrong):**
```
Upload same image → Create new document → version resets to 1
```

**After (✅ Correct):**
```
Upload same image → Check hash → Load existing document → Show latest version
```

## 📊 Correct Version Flow

### Case 1: First Upload
```
Document 1 | hash: abc123 | version: 1 | status: ocr | text: [raw OCR]
```

### Case 2: Human Correction
```
Document 1 | hash: abc123 | version: 2 | status: corrected | text: [verified]
                                                              cer: 0.05
```

### Case 3: Re-upload Same Image
**System behavior:**
- Computes hash: `abc123`
- Finds existing document
- **Loads version 2 (corrected text)**
- Shows: "This document already exists. Showing verified version."
- **Does NOT run OCR again** (unless explicitly requested)

### Case 4: Explicit Reprocessing
User clicks "Re-run OCR":
```
Document 1 | hash: abc123 | version: 3 | status: ocr_improved | text: [new OCR]
                                                                  parent_id: 1
                                                                  cer: 0.03
```

## 🎨 Frontend Behavior

### Upload Flow
1. **File selected** → Compute hash
2. **Check database:**
   - **Exists + corrected**: Show blue info box
     > 📋 This document already exists (v2). Showing verified version (CER: 0.05).
   - **Exists + not corrected**: Show info
     > 📋 This document already exists (v1). Click Parse to see results.
   - **New**: Normal flow

### Process Flow
1. **Parse button clicked** → Check `force_reprocess` flag
2. **If NOT forced:**
   - Return corrected text if available
   - Return cached OCR if no correction yet
3. **If forced:**
   - Run OCR again
   - Create new version (v3, v4, etc.)
   - Compute CER against corrected text

## 🔄 API Changes

### `/upload` (POST)
**Returns:**
```json
{
  "success": true,
  "filepath": "uploads/image.jpg",
  "image_hash": "abc123...",
  "existing_document": true,
  "doc_id": 42,
  "status": "corrected",
  "version": 2,
  "has_correction": true,
  "cer": 0.0523,
  "message": "This image already exists. Showing latest version."
}
```

### `/process` (POST)
**Request:**
```json
{
  "filepath": "uploads/image.jpg",
  "mode": "fast",
  "image_hash": "abc123...",
  "force_reprocess": false
}
```

**Response (existing document):**
```json
{
  "success": true,
  "reused_existing": true,
  "doc_id": 42,
  "full_text": "[corrected text]",
  "version": 2,
  "status": "corrected",
  "cer": 0.0523,
  "message": "Showing verified corrected version. Click 'Re-run OCR' to reprocess."
}
```

### `/reprocess/<doc_id>` (POST)
Explicitly triggers OCR reprocessing for existing document.

### `/review/<doc_id>` (GET/POST)
Now includes **version_history** showing all versions of the document.

## ✅ What This Achieves

### 1. **Human-in-the-Loop Preservation**
- Corrected text is **never lost**
- Re-uploading same image shows human corrections
- No wasted scholarly effort

### 2. **Proper Versioning**
```
Document ID | Image Hash | Version | Type
------------|------------|---------|------------
1           | abc123     | 1       | raw OCR
1           | abc123     | 2       | corrected
1           | abc123     | 3       | improved OCR
```
All versions belong to **same document**, not separate entries.

### 3. **CER Tracking Over Time**
```
v1 → v2: CER = 0.15 (human correction)
v2 → v3: CER = 0.05 (system learns)
v3 → v4: CER = 0.02 (continuous improvement)
```

### 4. **Project Goals Alignment**
✔ Scholarly rigor (corrections preserved)  
✔ Dataset versioning (proper history)  
✔ Quality metrics (CER reduction visible)  
✔ Learning loop foundation (ready for model retraining)

## 🚫 What NOT to Do

❌ **Don't** create new document for same image  
❌ **Don't** reset version numbers  
❌ **Don't** recompute OCR blindly  
❌ **Don't** lose corrected text  
❌ **Don't** show OCR output when correction exists  

## 🧪 Testing the Flow

### Test 1: First Upload
```bash
# Upload manuscript image
curl -F "file=@manuscript.jpg" http://localhost:5000/upload
# Expected: existing_document = false
```

### Test 2: Re-upload Same Image
```bash
# Upload same image again
curl -F "file=@manuscript.jpg" http://localhost:5000/upload
# Expected: existing_document = true, doc_id = same as before
```

### Test 3: Process Existing Document
```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{"filepath":"uploads/manuscript.jpg","image_hash":"abc123","force_reprocess":false}'
# Expected: reused_existing = true, returns corrected text if available
```

### Test 4: Force Reprocess
```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{"filepath":"uploads/manuscript.jpg","image_hash":"abc123","force_reprocess":true}'
# Expected: Runs OCR again, creates version 3
```

## 📝 Database Queries

### Find all versions of a document:
```sql
SELECT id, version, status, cer, created_at 
FROM documents 
WHERE image_hash = 'abc123...'
ORDER BY version ASC;
```

### Get latest version:
```sql
SELECT * FROM documents 
WHERE image_hash = 'abc123...'
ORDER BY version DESC 
LIMIT 1;
```

### Track CER improvement:
```sql
SELECT version, cer, status, updated_at
FROM documents
WHERE image_hash = 'abc123...'
AND cer IS NOT NULL
ORDER BY version ASC;
```

## 🔧 Troubleshooting

### Issue: "Document not found" on re-upload
**Cause**: Database not migrated  
**Solution**: Run `python migrate_db.py`

### Issue: Always creates new documents
**Cause**: `image_hash` not being computed/sent  
**Solution**: Check upload endpoint, ensure hash is returned

### Issue: CER not calculating
**Cause**: No corrected text to compare against  
**Solution**: First correct the document via `/review/<doc_id>`

## 🎓 Academic Significance

This implementation directly supports the research goals:

1. **Reproducibility**: Same image = same document identity
2. **Provenance**: Complete version history preserved
3. **Quality Metrics**: CER tracked across iterations
4. **Human Expertise**: Corrections are authoritative, not discarded
5. **Continuous Improvement**: System can learn from corrections (future work)

---

**Next Steps:**
- Add visual version history UI in review page
- Implement side-by-side comparison of versions
- Add batch reprocessing for model improvement testing
- Export corrected dataset for model fine-tuning
