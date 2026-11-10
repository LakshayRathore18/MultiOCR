# MultiOCR document workflow

This guide describes the current web flow implemented in `web/app.py`.

## 1. Upload

`POST /upload` validates the extension, writes the image to `uploads/`, and initializes draft state. The response contains the saved filepath. This step does not create a document row or embedding.

## 2. Run OCR

`POST /process` accepts `filepath` and `mode` (`paddleocr`, `easyocr`, `deepseek`, or `multiocr`). It runs the selected processing, normalizes text, and returns original text, line confidence, available benchmarks, and quality metrics.

The result is an unsaved draft with `doc_id: null`, `status: ocr`, `has_correction: false`, and no last-edited timestamp. Running OCR again produces another fresh draft. Previously saved corrections never replace this output automatically.

## 3. Find references

After displaying OCR, the browser independently calls `POST /similar-documents` with the raw text and optional saved document ID.

The search generates a temporary query embedding and compares it against original-OCR and correction embeddings in saved records. It uses the stronger valid cosine match per record, falling back to word overlap only when neither vector is usable. Results include both texts and the matching source.

Only the latest 100 saved records are candidates. The current document is excluded and the default threshold is 0.3. Home cards initially show the top three, with View more adding three. Each paired text box scrolls independently and copies its complete text. Empty, loading, failed/retry, and stale-request states are handled in `similar_documents.js`.

## 4. Review and correction

`GET /review/new` loads original text from active draft memory. `GET /review/{doc_id}` loads a saved document and uses its original OCR for reference search. The review page shows up to five reference documents.

The user can type corrections, detect possible errors, request Auto Fix, and add learned words or confusion pairs. The page displays Original OCR, whether a correction has been saved, and the last document edit time where available.

Auto Fix for a new draft returns a preview without creating a row. For a saved document, the current `/correct` route persists the generated correction immediately and refreshes its vector and timestamp. The original OCR remains unchanged.

## 5. First save

`POST /review/new` requires nonempty corrected text and an active OCR draft. It:

1. Reads original OCR from the active draft.
2. Calculates CER against the submitted correction.
3. Generates an embedding from the original OCR.
4. Generates another embedding from the correction.
5. Inserts both texts, both vectors, workflow state, and timestamps into one row.
6. Returns the new document ID and save information.

The text survives an embedding failure; the corresponding vector is null and can be rebuilt later.

## 6. Later saves

`POST /review/{doc_id}` updates the existing row's correction, CER, correction vector, workflow state, and last-edited timestamp. It preserves original OCR and its vector. Earlier corrections are overwritten; there is no previous-edit restore feature.

Save metadata is returned to the browser and updated in the active draft when it refers to the same saved document. Restoring the home page therefore retains original OCR alongside accurate save information.

## 7. Database maintenance

Run from the project root with the intended PostgreSQL `.env` configuration:

```powershell
python -m database.setup_database       # New installation
python -m database.migrate_db           # Upgrade existing schema
python -m database.backfill_embeddings  # Rebuild stored vectors from source texts
```

Migration removes obsolete metadata columns while preserving the actual documents. The backfill processes records in batches, skips empty source text, and checks that the texts have not changed before writing vectors.

## 8. Validation

```powershell
python -m unittest discover -s tests -p "test_dual_embeddings.py"
node --test tests/test_similar_documents.cjs tests/test_document_status.cjs
```

Focused checks cover dual-vector ranking, original preservation, correction updates, save timestamps, reference rendering, migration behavior, and asynchronous search/reset behavior without loading OCR models.

## Data and deployment notes

`ocr_embedding` encodes `ocr_text`; `text_embedding` encodes `corrected_text`. CER measures difference between those texts, not accuracy against an independently supplied ground truth. The server currently shares active draft memory across users and loses unsaved drafts on restart.
