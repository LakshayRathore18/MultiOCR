# MultiOCR Complete Flow Documentation

## Overview
This document traces the complete data flow from image upload to final OCR result and editing, covering all four OCR modes: PaddleOCR, EasyOCR, DeepSeek, and MultiOCR.

---

## Phase 1: Application Startup

### File: `web/app.py`

**Model Initialization (Lines 50-91)**
```python
# Initialize OCR models at startup
paddle_model = init_paddle_model()  # From ocr/paddle_ocr.py
easy_model = init_easy_model()      # From ocr/easy_ocr.py  
deepseek_model = init_deepseek_model()  # From ocr/deepseek_ocr.py

# Initialize PostOCR correction module
postocr_corrector = get_corrector()  # From postocr_integration.py
```

**What happens:**
1. PaddleOCR model loads with Hindi language support
2. EasyOCR model loads with Hindi language (may download models on first run)
3. DeepSeek OCR connects to Ollama API at `http://localhost:11434`
4. PostOCR corrector loads dictionary, confusion pairs, and domain words
5. All models are stored in global variables for reuse

---

## Phase 2: Image Upload

### File: `web/app.py` - Upload Endpoint (Lines 114-186)

**Route:** `POST /upload`

**Step-by-Step Flow:**

1. **File Validation (Lines 114-123)**
   - Check if file exists in request
   - Validate file extension (PNG, JPG, JPEG, GIF, BMP, TIFF)
   - Return error if invalid

2. **Image Hash Computation (Lines 125-127)**
   ```python
   file_bytes = file.read()
   image_hash = compute_image_hash(file_bytes)  # From src/utils/image_hash.py
   ```
   - **File:** `src/utils/image_hash.py` (Lines 6-17)
   - Computes SHA256 hash of image bytes
   - Creates unique fingerprint for deduplication

3. **File Storage (Lines 129-134)**
   - Reset file pointer
   - Generate secure filename
   - Save to `uploads/` directory

4. **Database Deduplication Check (Lines 136-147)**
   ```python
   conn = get_db()  # From src/database/db.py
   cur.execute("SELECT id, image_path, corrected_text, status, version, cer 
               FROM documents WHERE image_hash = %s", (image_hash,))
   ```
   - **File:** `src/database/db.py` (Lines 8-19)
   - Connects to PostgreSQL using environment variables
   - Checks if image hash already exists in database

5. **Duplicate Handling (Lines 149-172)**
   - If duplicate found: Return existing document data
   - Store in session for persistence
   - Return success with `existing_document: True`

6. **New Document Handling (Lines 174-186)**
   - Store metadata in session
   - Return success with `existing_document: False`

**Session Data Stored:**
- `current_filename`
- `current_filepath`
- `current_image_hash`
- `current_doc_id` (if existing)
- `current_status` (if existing)

---

## Phase 3: OCR Processing

### File: `web/app.py` - Process Endpoint (Lines 188-494)

**Route:** `POST /process`

**Parameters:**
- `filepath`: Path to uploaded image
- `mode`: OCR mode ('paddleocr', 'easyocr', 'deepseek', 'multiocr')
- `image_hash`: SHA256 hash of image
- `force_reprocess`: Boolean to skip cached results

**Step-by-Step Flow:**

### 3.1: Cache Check (Lines 196-254)

```python
if image_hash and not force_reprocess:
    conn = get_db()
    cur.execute("SELECT id, ocr_text, corrected_text, cer, status, version 
                FROM documents WHERE image_hash = %s", (image_hash,))
```

**If corrected version exists:**
- Return corrected text with CER score
- Status: 'corrected', version: 2

**If OCR version exists:**
- Return OCR text
- Status: 'ocr', version: 1

**If no cache:**
- Proceed to OCR processing

### 3.2: OCR Mode Selection (Lines 256-434)

#### Mode A: PaddleOCR (Lines 257-290)

```python
if mode == 'paddleocr':
    paddle_data = benchmark_ocr(lambda path: run_paddleocr(path, paddle_model), filepath)
    final_output = paddle_data["results"]
```

**Flow:**
1. **File:** `ocr/benchmark.py` (Lines 3-18)
   - Starts timer
   - Calls OCR function
   - Measures execution time
   - Calculates average confidence
   - Returns: `{time_sec, lines, avg_confidence, results}`

2. **File:** `ocr/paddle_ocr.py` (Lines 13-32)
   ```python
   def run_paddleocr(image_path, model=None):
       result = model.predict(input=image_path)
       output = []
       for res in result:
           texts = res.get("rec_texts", [])
           scores = res.get("rec_scores", [])
           for text, score in zip(texts, scores):
               output.append({"text": text, "confidence": float(score)})
       return output
   ```
   - Runs PaddleOCR prediction
   - Extracts text and confidence scores
   - Returns standardized format: `[{"text": str, "confidence": float}]`

3. **Quality Metrics (Lines 263-265)**
   ```python
   full_text = '\n'.join([item['text'] for item in final_output])
   quality_metrics = validate_ocr_text(full_text)  # From ocr/normalize.py
   ```
   - Calculates Devanagari quality score
   - Detects potential OCR issues

4. **Response Construction (Lines 267-290)**
   ```python
   results = {
       'success': True,
       'mode': 'paddleocr',
       'benchmark': {'paddleocr': {time, lines, avg_confidence}},
       'devanagari_quality': {score, issues_found, devanagari_chars},
       'text': [{'text': str, 'confidence': float}],
       'full_text': str
   }
   ```

#### Mode B: DeepSeek (Lines 291-326)

```python
elif mode == 'deepseek':
    deepseek_data = benchmark_ocr(lambda path: run_deepseek(path, deepseek_model), filepath)
    final_output = deepseek_data["results"]
```

**Flow:**
1. **File:** `ocr/deepseek_ocr.py` (Lines 22-185)
   ```python
   class DeepSeekEngine:
       def __init__(self, api_url, model):
           self.api_url = os.getenv("DEEPSEEK_API_URL", "http://localhost:11434/api/chat")
           self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-ocr")
       
       def _encode_image(self, image_path):
           img = Image.open(image_path).convert("RGB")
           buffered = io.BytesIO()
           img.save(buffered, format="PNG")
           return base64.b64encode(buffered.getvalue()).decode()
   ```
   - Encodes image to base64
   - Sends to Ollama API
   - Uses LLM-based text recognition
   - Returns standardized format

2. **Same quality metrics and response construction as PaddleOCR**

#### Mode C: EasyOCR (Lines 327-364)

```python
elif mode == 'easyocr':
    easy_data = benchmark_ocr(lambda path: run_easyocr(path, easy_model), filepath)
    final_output = easy_data["results"]
```

**Flow:**
1. **File:** `ocr/easy_ocr.py` (Lines 41-203)
   ```python
   def run_easyocr(image_path, model=None):
       result = model.readtext(image_path)
       output = []
       for detection in result:
           bbox, text, confidence = detection
           output.append({"text": text, "confidence": float(confidence)})
       return output
   ```
   - Runs EasyOCR with Hindi model
   - Extracts bounding boxes, text, confidence
   - Returns standardized format

2. **Same quality metrics and response construction as PaddleOCR**

#### Mode D: MultiOCR (Lines 365-434)

```python
else:  # multiocr mode
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        paddle_future = executor.submit(benchmark_ocr, lambda path: run_paddleocr(path, paddle_model), filepath)
        easy_future = executor.submit(benchmark_ocr, lambda path: run_easyocr(path, easy_model), filepath) if easy_model else None
        deepseek_future = executor.submit(benchmark_ocr, lambda path: run_deepseek(path, deepseek_model), filepath) if deepseek_model else None
```

**Flow:**
1. **Parallel Execution**
   - Runs PaddleOCR, EasyOCR, and DeepSeek simultaneously
   - Uses ThreadPoolExecutor for concurrent processing

2. **Result Collection (Lines 383-385)**
   ```python
   paddle_data = paddle_future.result()
   easy_data = easy_future.result() if easy_future else None
   deepseek_data = deepseek_future.result() if deepseek_future else None
   ```

3. **Primary Result Selection (Line 388)**
   ```python
   final_output = paddle_data["results"]  # Use PaddleOCR as primary
   ```

4. **Benchmark Dictionary Construction (Lines 395-415)**
   - Collects metrics from all available engines
   - Returns comprehensive performance data

5. **Same quality metrics and response construction**

### 3.3: Database Storage (Lines 434-494)

**Version Management (Lines 438-452)**
```python
if image_hash:
    cur.execute("SELECT id, version FROM documents WHERE image_hash = %s", (image_hash,))
    existing = cur.fetchone()
    if existing:
        parent_id = existing[0]
        current_version = existing[1] + 1
```

**Text Embedding Generation (Lines 454-460)**
```python
text_for_embedding = results['full_text']
embedding = embed_text(text_for_embedding)  # From similarity/embeddings.py
```
- **File:** `similarity/embeddings.py` (Lines 20-35)
  - Uses sentence-transformers (all-MiniLM-L6-v2)
  - Generates semantic embedding vector
  - Returns list of floats

**Database Insert (Lines 462-474)**
```python
cur.execute("""
    INSERT INTO documents (image_path, image_hash, ocr_text, status, version, parent_id, text_embedding)
    VALUES (%s, %s, %s, 'ocr', %s, %s, %s)
    RETURNING id
""", (filepath, image_hash, results['full_text'], current_version, parent_id, json.dumps(embedding)))
```

**Session Update (Lines 476-489)**
- Stores `current_doc_id`, `current_filepath`, `current_image_hash`, `current_status`
- Stores complete OCR results in session

**Response (Line 491)**
- Returns OCR results with `doc_id`, `version`, `is_reprocess`

---

## Phase 4: Auto-Correction

### File: `web/app.py` - Correct Endpoint (Lines 777-836)

**Route:** `POST /correct`

**Flow:**

1. **Input Validation (Lines 782-789)**
   ```python
   ocr_text = data.get('text', '')
   doc_id = data.get('doc_id')
   confidence_threshold = data.get('confidence_threshold', 'MEDIUM')
   ```

2. **PostOCR Correction (Lines 791-796)**
   ```python
   from postocr_integration import correct_text
   result = correct_text(ocr_text, confidence_threshold)
   ```
   - **File:** `postocr_integration.py` (Lines 93-125)
   ```python
   def correct_text(text, confidence_threshold='MEDIUM'):
       corrector = get_corrector()
       errors = corrector.detect_errors(text)
       corrected = corrector.auto_correct(text, confidence_threshold)
       return {
           'success': True,
           'corrected_text': corrected,
           'errors_found': len(errors),
           'errors': errors,
           'confidence_threshold': confidence_threshold
       }
   ```

3. **PostOCR Internal Flow:**
   - **File:** `postOCR/src/core/corrector.py` (referenced in postocr_integration.py)
   - Loads dictionary with 360K+ words
   - Uses trie-based word lookup
   - Matches against learned confusion pairs
   - Checks domain-specific vocabulary (Sanskrit, Samhita)
   - Applies corrections based on confidence threshold

4. **Database Update (Lines 814-831)**
   ```python
   cer = compute_cer(ocr_text, corrected_text)  # From src/utils/cer.py
   cur.execute("""
       UPDATE documents 
       SET corrected_text = %s, status = 'corrected', cer = %s 
       WHERE id = %s
   """, (corrected_text, cer, doc_id))
   ```
   - **File:** `src/utils/cer.py` (Lines 3-17)
   ```python
   def compute_cer(pred, gt):
       return Levenshtein.distance(pred, gt) / max(len(gt), 1)
   ```
   - Calculates Character Error Rate using Levenshtein distance

5. **Response (Lines 833-836)**
   - Returns corrected text, corrections made, CER score

---

## Phase 6: Manual Review & Edit

### File: `web/app.py` - Review Endpoint (Lines 601-775)

**Route:** `GET/POST /review/<int:doc_id>`

### 6.1: GET Request - Display Review Form (Lines 721-775)

**Flow:**

1. **Fetch Document (Lines 722-733)**
   ```python
   cur.execute("""
       SELECT image_path, ocr_text, corrected_text, cer, status, version, image_hash, parent_id 
       FROM documents WHERE id=%s
   """, (doc_id,))
   ```

2. **Fetch Version History (Lines 735-745)**
   ```python
   cur.execute("""
       SELECT id, version, status, cer, created_at, updated_at
       FROM documents WHERE image_hash = %s 
       ORDER BY version ASC
   """, (image_hash,))
   ```

3. **Find Similar Documents (Lines 747-760)**
   ```python
   similar_docs = find_similar_documents(
       current_text=corrected_text if corrected_text else ocr_text,
       current_doc_id=doc_id,
       threshold=0.3,
       limit=5
   )
   ```
   - **File:** `similarity/search.py` (Lines 64-133)
   ```python
   def find_similar_documents(current_text, current_doc_id, threshold, limit):
       # Fetch recent documents from database
       # Compute word-level Jaccard similarity
       # Return top matches above threshold
   ```
   - Uses word-level similarity (Jaccard index)
   - Helps find reference documents for manual correction

4. **Render Template (Lines 764-775)**
   - Returns HTML review page with OCR text, corrections, similar docs

### 6.2: POST Request - Save Corrections (Lines 611-699)

**Flow:**

1. **Extract Corrected Text (Lines 615-621)**
   ```python
   if request.is_json:
       corrected = data.get('corrected_text', '').strip()
   else:
       corrected = request.form.get('corrected_text', '').strip()
   ```

2. **Fetch Original OCR Text (Lines 630-646)**
   ```python
   cur.execute("SELECT ocr_text FROM documents WHERE id=%s", (doc_id,))
   ocr_text = result[0] or ''
   ```

3. **Compute CER (Lines 648-650)**
   ```python
   cer = compute_cer(ocr_text, corrected) if ocr_text else None
   ```
   - **File:** `src/utils/cer.py`
   - Measures improvement from manual correction

4. **Generate Embedding (Lines 652-658)**
   ```python
   embedding = embed_text(corrected)
   ```
   - **File:** `similarity/embeddings.py`
   - Generates embedding for corrected text (more accurate than OCR)

5. **Database Update (Lines 666-678)**
   ```python
   cur.execute("""
       UPDATE documents
       SET corrected_text=%s, cer=%s, status='corrected', version=2, 
           text_embedding=%s, updated_at=NOW()
       WHERE id=%s
   """, (corrected, cer, json.dumps(embedding), doc_id))
   ```

6. **Verification (Lines 686-693)**
   - Fetches updated document to verify save
   - Logs verification results

7. **Session Cleanup (Lines 698-705)**
   - Clears session data on successful save

8. **Response (Lines 707-719)**
   - Returns success message with CER score

---

## Phase 7: Voting System (MultiOCR Mode)

### File: `ocr/voting.py`

**Function:** `ocr_voting()` (Lines 29-87)

**Purpose:** Compare OCR results from multiple engines and select best output

**Flow:**

1. **Input Parameters:**
   - `paddle_results`: Results from PaddleOCR
   - `deepseek_results`: Results from DeepSeek OCR
   - `min_confidence`: Minimum confidence threshold (default 0.6)

2. **Line Count Analysis (Lines 49-56)**
   ```python
   line_counts = [len(paddle_results)]
   if deepseek_results:
       line_counts.append(len(deepseek_results))
   same_line_count = len(set(line_counts)) == 1
   ```

3. **Iterate Through Lines (Lines 58-86)**
   ```python
   for i in range(max_len):
       p = paddle_results[i] if i < len(paddle_results) else None
       d = deepseek_results[i] if deepseek_results and i < len(deepseek_results) else None
   ```

4. **Text Normalization (Lines 62-66)**
   ```python
   if p:
       p["text"] = normalize_text(p["text"])
   if d:
       d["text"] = normalize_text(d["text"])
   ```
   - **File:** `ocr/normalize.py` (not shown in detail)
   - Normalizes text for comparison

5. **Confidence-Based Voting (Lines 68-74)**
   ```python
   candidates = [x for x in [p, d] if x is not None]
   selected = max(candidates, key=lambda x: x["confidence"])
   ```
   - Selects result with highest confidence

6. **Duplicate Filtering (Lines 76-85)**
   - If same line count: Keep all lines (no filtering)
   - If different line counts: Apply duplicate detection
   - Uses `is_duplicate()` function (Lines 8-27)

7. **Return Final Results**
   - List of best OCR results per line
   - Deduplicated and confidence-filtered

---

## Phase 8: Similarity Search

### File: `similarity/search.py`

**Function:** `find_similar_documents()` (Lines 64-133)

**Purpose:** Find similar documents for reference during manual correction

**Flow:**

1. **Input Parameters:**
   - `current_text`: Text of current document
   - `current_doc_id`: ID to exclude from results
   - `threshold`: Minimum similarity score (default 0.3)
   - `limit`: Maximum results (default 5)

2. **Database Query (Lines 81-102)**
   ```python
   cur.execute("""
       SELECT id, corrected_text, ocr_text, image_path, cer, status, version
       FROM documents WHERE id != %s
       ORDER BY updated_at DESC LIMIT 100
   """, (current_doc_id,))
   ```

3. **Word Similarity Calculation (Lines 105-116)**
   ```python
   compare_text = corrected_text if corrected_text else ocr_text
   score = word_similarity(current_text, compare_text)
   ```
   - **Function:** `word_similarity()` (Lines 30-62)
   - Uses Jaccard similarity on word tokens
   - Splits on whitespace and Devanagari punctuation
   - Calculates: intersection / union of word sets

4. **Filter and Sort (Lines 117-131)**
   - Filters results above threshold
   - Sorts by similarity score (highest first)
   - Returns top N results

5. **Return Format:**
   ```python
   [{
       "doc_id": int,
       "score": float,
       "text": str (preview),
       "full_text": str,
       "image_path": str,
       "cer": float,
       "status": str,
       "version": int,
       "has_correction": bool
   }]
   ```

---

## Complete Data Flow Summary

### User Action: Upload Image
1. **Frontend:** User selects image and clicks upload
2. **web/app.py:** `/upload` endpoint validates and stores file
3. **src/utils/image_hash.py:** Computes SHA256 hash
4. **src/database/db.py:** Checks for duplicates
5. **Response:** Returns filepath and hash to frontend

### User Action: Select OCR Mode & Process
1. **Frontend:** User selects mode (paddleocr/easyocr/deepseek/multiocr)
2. **web/app.py:** `/process` endpoint receives request
3. **Cache Check:** Database query for existing results
4. **OCR Execution:**
   - **PaddleOCR:** `ocr/paddle_ocr.py` → `ocr/benchmark.py`
   - **EasyOCR:** `ocr/easy_ocr.py` → `ocr/benchmark.py`
   - **DeepSeek:** `ocr/deepseek_ocr.py` → `ocr/benchmark.py`
   - **MultiOCR:** All three in parallel → `ocr/voting.py`
5. **Quality Metrics:** `ocr/normalize.py`
6. **Embedding:** `similarity/embeddings.py`
7. **Database Storage:** `src/database/db.py` (INSERT with version)
8. **Response:** Returns OCR results with benchmark data

### User Action: Auto-Correct
1. **Frontend:** User clicks "Auto-Correct"
2. **web/app.py:** `/correct` endpoint receives OCR text
3. **postocr_integration.py:** Loads corrector with dictionary
4. **PostOCR:** Detects errors using confusion pairs and domain words
5. **CER Calculation:** `src/utils/cer.py`
6. **Database Update:** `src/database/db.py` (UPDATE with corrected text)
7. **Response:** Returns corrected text with CER

### User Action: Manual Review & Edit
1. **Frontend:** User navigates to review page
2. **web/app.py:** `/review/<id>` GET endpoint
3. **Database Query:** Fetch document and version history
4. **Similarity Search:** `similarity/search.py` finds reference docs
5. **Response:** Renders review page with similar documents
6. **Frontend:** User edits text and saves
7. **web/app.py:** `/review/<id>` POST endpoint
8. **CER Calculation:** `src/utils/cer.py`
9. **Embedding Update:** `similarity/embeddings.py`
10. **Database Update:** `src/database/db.py` (UPDATE with corrections)
11. **Response:** Returns success with CER

---

## File Dependency Map

```
web/app.py (Main Flask Application)
├── src/database/db.py (Database connection)
├── src/utils/image_hash.py (Image hashing)
├── src/utils/cer.py (Character Error Rate)
├── similarity/embeddings.py (Text embeddings)
├── similarity/search.py (Similarity search)
├── postocr_integration.py (PostOCR correction)
│   └── postOCR/src/core/corrector.py (Core correction logic)
├── ocr/paddle_ocr.py (PaddleOCR engine)
├── ocr/easy_ocr.py (EasyOCR engine)
├── ocr/deepseek_ocr.py (DeepSeek OCR engine)
├── ocr/voting.py (OCR voting system)
├── ocr/benchmark.py (Benchmarking utilities)
├── ocr/normalize.py (Text normalization)
```

---

## Database Schema

### Table: documents

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| image_path | TEXT | Path to uploaded image |
| image_hash | VARCHAR(64) | SHA256 hash for deduplication |
| ocr_text | TEXT | Raw OCR output (v1) |
| corrected_text | TEXT | Human-corrected text (v2) |
| cer | FLOAT | Character Error Rate |
| parent_id | INTEGER | Parent document ID for version tracking |
| version | INTEGER | Document version (1=OCR, 2=Corrected) |
| status | VARCHAR | pending/ocr/corrected/reviewed |
| text_embedding | JSONB | Text embedding vector |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### Indexes
- `idx_image_hash`: Fast hash-based lookups
- `idx_parent_id`: Version tracking queries
- `idx_status`: Status filtering
- `idx_created_at`: Time-based sorting

---

## Key Design Patterns

### 1. Hash-Based Deduplication
- SHA256 hash prevents re-processing identical images
- Instant retrieval of cached results
- Supports version tracking for re-processing

### 2. Multi-Model OCR with Voting
- Parallel execution of multiple OCR engines
- Confidence-based voting selects best results
- Duplicate filtering for varying line counts

### 3. Version Control
- v1: Raw OCR output
- v2: Human-corrected text
- Parent-child relationships track document evolution

### 4. Post-OCR Correction
- Dictionary-based correction (360K+ words)
- Learned confusion pairs from OCR errors
- Domain-specific vocabulary (Sanskrit, Samhita)
- Trie-based efficient word lookup

### 5. Human-in-the-Loop
- Manual review interface
- Similarity search for reference documents
- CER tracking for quality measurement
- Session persistence across navigation

### 6. Semantic Similarity
- Sentence-transformers for text embeddings
- Word-based Jaccard similarity
- Helps find similar documents for correction reference

---

## Environment Variables

Required in `.env` file:

```env
# Database
DB_NAME=multiocrDB
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# GPU Configuration
USE_GPU=true

# DeepSeek OCR
DEEPSEEK_API_URL=http://localhost:11434/api/chat
DEEPSEEK_MODEL=deepseek-ocr
```

---

## Performance Considerations

1. **Model Initialization:** All OCR models loaded at startup to avoid per-request delays
2. **Parallel Processing:** MultiOCR mode uses ThreadPoolExecutor for concurrent OCR
3. **Lazy Loading:** Sentence-transformers model loaded on first use
4. **Caching:** Hash-based deduplication prevents redundant processing
5. **Session Persistence:** Reduces database queries for repeated operations

---

## Error Handling

1. **Model Loading Failures:** Graceful degradation with warnings
2. **Database Errors:** Transaction rollback on failure
3. **OCR Failures:** Individual engine failures don't break entire pipeline
4. **File Validation:** Comprehensive checks before processing
5. **API Errors:** Try-catch blocks with user-friendly error messages

---

## Security Considerations

1. **File Upload:** Secure filename generation, extension validation
2. **Database:** Parameterized queries to prevent SQL injection
3. **Session Management:** Permanent sessions with secure keys
4. **Environment Variables:** Sensitive data in .env file
5. **File Size Limits:** 16MB max upload size

---

This completes the comprehensive flow documentation for MultiOCR from image upload to final OCR result and editing.
