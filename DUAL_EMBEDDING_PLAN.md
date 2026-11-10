# Dual OCR embedding search plan

## Agreed behavior

Store the original OCR text and saved correction in the same document record.
Keep two vectors: `ocr_embedding` for original OCR and existing `text_embedding`
for the saved correction. Use the current raw OCR as the search query against
both vectors. Rank each document by its stronger valid cosine match and return
it only once (raw OCR wins ties).

Always show both **Original OCR** and **Saved Correction** for every result,
regardless of which version matched. Show “No saved correction” when absent.
Provide separate copy actions and retain the document link. Results remain
references. Upload processing always returns fresh OCR; similar documents never
automatically replace it with a previous record's text or correction.
Show references automatically below the OCR output on the home page as well as
on the review page. Home-page search loads independently after OCR, with loading,
empty, failure/retry states and cancellation when the upload changes.
On the home page, references sit below and outside the upload/output box, in
compact cards. Initially show the top three; View more reveals three more at a
time, and View less returns to three. Home search returns matches from the
existing latest-100 candidate pool; review pages retain their five-result limit.

## Implementation

1. Add nullable `ocr_embedding JSONB` to setup and the idempotent migration.
2. New document saves generate both vectors. Correction edits refresh only
   `text_embedding`, including `/correct`, and preserve original OCR and vector.
   Embedding failures save null instead of leaving stale vectors.
3. Both review routes query with raw OCR. Search both stored vectors, use the
   higher cosine score, then apply the existing 0.3 threshold and five-result
   limit over the latest 100 records. Exclude the current document.
4. If neither vector can be compared, use the stronger word-overlap match
   against the two texts. Do not mix cosine and word-overlap scores.
5. Extend results with both texts, both scores and `matched_on`; retain existing
   fields. Missing scores are null. Display paired text previews and copy tools.
6. Supply a separate rerunnable backfill command that rebuilds both vectors
   from their own source text, reports failures, and skips empty text. Protect
   against overwriting vectors when source text changes during the backfill.

## Validation and rollout

Test either match winning, ties, thresholds, ordering, deduplication, missing or
invalid vectors, fallback, original preservation, correction refresh/failure,
paired display, missing corrections, and multiline/quoted Devanagari text.
Use mocked database and embeddings for automated checks without OCR downloads.

From the `multiocr` directory, with the application's environment configured:

```powershell
python -m database.migrate_db
python -m database.backfill_embeddings
python -m unittest discover -s tests -p test_dual_embeddings.py -v
node --test tests/test_similar_documents.cjs
```

Apply the schema migration before deploying the updated search/save queries,
then backfill existing records. Keep the current model and candidate limit;
model selection and chunking are outside this task.

## Progress

- Final UI keeps only the section/document icons, with blue information strips
  and blue/green text accents. Removed the forced 700px OCR-panel minimum
  height to avoid empty space below the panels. All 21 Python and 8 frontend
  tests pass, along with JavaScript syntax and whitespace checks.

- Added the original UI's blue information strips to reference-card headers,
  colorful document/action icons, blue OCR and green correction accents, and
  blue document/expansion buttons. Kept all text boxes independently scrollable.

- Matched the home references to the existing white outer panels, section
  heading and purple divider, and reused the output-card styling. Each paired
  text box now scrolls independently with keyboard access instead of clipping
  after three lines. Kept the compact grid and top-three/View more behavior.

- Kept the original theme and moved only home-page references outside the main
  upload/output box. Added a responsive compact card grid and three-at-a-time
  expansion, preserving paired texts and full-text copy actions.
- Home `/similar-documents` now returns up to 100 ranked matches for View more;
  the initial rendered set is three. Resetting the upload resets expansion.

- At the user's request, reverted the UI redesigns to the original project
  styling, split-panel layout, controls and labels. Removed the added shared
  base stylesheet, new toolbars and collapsible layout changes. Retained the
  requested home/review reference cards with both texts and dual-vector search.
- Rechecked all 21 Python and 6 frontend tests after the rollback; all pass.

- Plan saved before implementation.
- Implemented dual-vector storage/search, correction embedding refresh, paired
  reference display, copy actions, schema migration, and guarded backfill.
- All 21 focused Python tests and 6 frontend tests passed, covering both match sources, fallback,
  save/update behavior, paired display and copy values, and backfill failures.
- Removed the previous 85% text-similarity automatic replacement path. Fresh
  OCR is always preserved; old OCR/corrections appear only as review references.
  Regression coverage checks this upload-to-review behavior for all three
  individual OCR engines, including an existing correction that used to match.
- Added `POST /similar-documents` (`text`, optional `doc_id`) for automatic
  home-page search. It returns `success` and `similar_docs`, uses the same dual
  ranking, and returns 503 on search failure without altering the OCR session.
- Added home-page paired text cards, independent copy actions, and a document
  link below the output. Tests cover literal Unicode/HTML-like text, both match
  sources, missing corrections, loading/empty/error states, retry, and stale
  responses after a new upload. Browser visual preview was unavailable.
- Applied the migration to the database configured in `multiocr/.env` and
  backfilled all 9 records using the cached model: 9 original OCR vectors and
  3 corrected-text vectors (the remaining records have no saved correction).
- Live read-only checks confirmed vector dimensions, raw OCR self-retrieval,
  current-document exclusion, and result texts paired with their stored record.
- Validation used `C:/Users/Lakshay/miniconda3/envs/multiocr/python.exe`; the
  broken `.venv` has since been moved to the ignored `venv.bak` directory.
