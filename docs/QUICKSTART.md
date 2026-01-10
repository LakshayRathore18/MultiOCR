# 🚀 Quick Start Guide - Hash-Based System

## Step 1: Run Database Migration

```bash
python migrate_db.py
```

Expected output:
```
✓ Column 'image_hash' added
✓ Column 'parent_id' added
✓ Index 'idx_image_hash' created
✅ Migration completed successfully!
```

## Step 2: Start the Application

```bash
python app.py
```

Or use the batch file:
```bash
start.bat
```

## Step 3: Test the Flow

### 🧪 Test Case 1: First Upload
1. Open http://localhost:5000
2. Upload a manuscript image
3. Click "Parse Document"
4. **Expected**: OCR runs normally, creates version 1

### 🧪 Test Case 2: Human Correction
1. Click "Review & Correct Text"
2. Fix any OCR errors
3. Click "Save Correction"
4. **Expected**: Version 2 created with CER calculated

### 🧪 Test Case 3: Re-upload Same Image
1. Go back to home
2. Upload THE SAME image again
3. **Expected**: Blue info box appears:
   > 📋 This document already exists (v2). Showing verified version (CER: 0.05).
4. Click "Parse Document"
5. **Expected**: Returns corrected text immediately (NO OCR runs)

### 🧪 Test Case 4: Force Reprocess
1. With same image uploaded, click "Re-run OCR"
2. Confirm the dialog
3. **Expected**: OCR runs again, creates version 3

### 🧪 Test Case 5: Version History
1. Navigate to review page
2. Scroll down
3. **Expected**: See timeline with all versions:
   - Version 1 (OCR)
   - Version 2 (Corrected, CER: X)
   - Version 3 (OCR, if reprocessed)

## 🎯 What You Should See

### Upload Response (New Image)
```json
{
  "success": true,
  "existing_document": false,
  "image_hash": "abc123..."
}
```

### Upload Response (Existing Image)
```json
{
  "success": true,
  "existing_document": true,
  "doc_id": 42,
  "version": 2,
  "has_correction": true,
  "cer": 0.0523
}
```

### Process Response (Existing + Corrected)
```json
{
  "success": true,
  "reused_existing": true,
  "doc_id": 42,
  "version": 2,
  "full_text": "[corrected text]",
  "message": "Showing verified corrected version..."
}
```

## 🐛 Troubleshooting

### "Column image_hash does not exist"
**Solution**: Run `python migrate_db.py`

### Always creates new documents
**Check**:
1. Migration ran successfully?
2. `image_hash` is being computed in upload?
3. Database connection working?

### CER not showing
**Reason**: Document needs human correction first
**Solution**: Use review page to submit corrected text

## 📊 Verify in Database

```sql
-- Check if columns exist
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='documents';

-- View all versions of a document
SELECT id, image_hash, version, status, cer, created_at
FROM documents
WHERE image_hash = 'abc123...'
ORDER BY version;

-- Find duplicates (should be none now!)
SELECT image_hash, COUNT(*) as count
FROM documents
GROUP BY image_hash
HAVING COUNT(*) > 1;
```

## ✅ Success Indicators

1. ✓ Same image upload shows "already exists"
2. ✓ Corrected text appears on re-upload (not raw OCR)
3. ✓ Version numbers increase per document
4. ✓ CER is calculated and stored
5. ✓ Version history displays correctly
6. ✓ Re-run OCR button appears for existing docs

## 🎓 Understanding the Flow

```
Upload Image
    ↓
Compute SHA256 hash
    ↓
Check database for hash
    ↓
┌─────────────┬─────────────┐
│  NOT FOUND  │    FOUND    │
├─────────────┼─────────────┤
│ Run OCR     │ Load latest │
│ Save v1     │ Return text │
│             │ Show info   │
└─────────────┴─────────────┘
```

---

**Need more help?** Check [HASH_SYSTEM.md](HASH_SYSTEM.md) for complete documentation.
