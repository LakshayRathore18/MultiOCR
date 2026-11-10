# MultiOCR

MultiOCR extracts Devanagari manuscript text with PaddleOCR, EasyOCR, and DeepSeek OCR, then lets you review and save corrections. Each saved document keeps its original OCR and latest correction together.

## Features

- Individual OCR engines and MultiOCR processing with voting/filtering.
- Dictionary suggestions, learned confusion pairs, and manual correction.
- Character Error Rate (CER), measuring the difference between original OCR and saved correction.
- Two document embeddings: original OCR and saved correction.
- Similar documents shown automatically below the main OCR box, with paired text, independent scrolling and copy actions.
- Top three references initially, with View more for additional matches.
- Clear Original OCR, Correction saved, and Last edited information.

## Setup

Run these commands from the project directory containing `requirements.txt`:

```powershell
conda create -n multiocr python=3.12 -y
conda activate multiocr
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure PostgreSQL using `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in `.env`. Use the same environment when running the server and database commands. Do not commit credentials.

For DeepSeek OCR, start Ollama and install the model used by the project:

```powershell
ollama pull deepseek-ocr
```

Create the database for a new installation:

```powershell
python -m database.setup_database
```

Upgrade an existing installation:

```powershell
python -m database.migrate_db
```

The migration removes obsolete document metadata while retaining document rows, original text, corrections, embeddings, and timestamps. It can be run again safely.

To generate both embeddings for existing text records:

```powershell
python -m database.backfill_embeddings
```

This uses the configured SentenceTransformer model. A model download is needed if it is not cached. The command reports failures and skips updates when source text changes during processing.

## Run

From the project directory:

```powershell
python -m uvicorn web.app:app --host 127.0.0.1 --port 5000 --reload
```

Open http://localhost:5000. You can also run `python app.py` from `web/` using the activated project environment.

## Document flow

1. Upload an image and select an OCR engine.
2. Parse it to produce fresh original OCR. The draft is held in memory.
3. A temporary query embedding searches saved documents against both stored text embeddings. References never replace the current output automatically.
4. Open Review & Correct Text, inspect suggestions, and edit the correction.
5. Save Correction creates the document row and stores the original OCR, correction, both embeddings, CER, and timestamps.
6. Later correction saves update the latest correction and its embedding. Original OCR and its embedding stay unchanged.

Re-running OCR starts a fresh draft. Saving that draft creates a separate document. A document keeps the latest correction; earlier correction edits cannot be restored. Auto Fix on an already saved document also persists its generated correction and refreshes its embedding and last-edited time.

## Stored document fields

| Field | Meaning |
| --- | --- |
| `id` | Saved document identifier |
| `image_path` | Uploaded image location |
| `ocr_text` | Original OCR output |
| `corrected_text` | Latest saved correction |
| `ocr_embedding` | Original OCR vector |
| `text_embedding` | Saved correction vector |
| `cer` | Original/correction character difference |
| `status` | Stored workflow state |
| `created_at` | Initial save time |
| `updated_at` | Last document update time |

The UI displays save information rather than revision numbers. A saved correction is not an independent guarantee that every word is correct.

## Similar documents

The current raw OCR is compared against both stored vectors. Each document is ranked by its stronger valid cosine match and returned once. If neither stored vector can be compared, the search uses word overlap against both texts. Both original OCR and correction are shown regardless of the matching source.

Search considers the latest 100 saved records, excludes the current saved document, and applies a 0.3 threshold. Home results expand three at a time; review results are limited to five. The default embedding model is `all-MiniLM-L6-v2`.

## Checks

```powershell
python -m unittest discover -s tests -p "test_dual_embeddings.py"
node --test tests/test_similar_documents.cjs tests/test_document_status.cjs
```

The focused tests mock OCR models and database access. They do not download models or modify your database.

## Project structure and documentation

- `web/`: FastAPI routes, Jinja templates, JavaScript, and CSS.
- `ocr/`: OCR engines, voting, normalization, and benchmarks.
- `correction/`: dictionary and correction logic.
- `similarity/`: embedding generation and dual-text search.
- `database/`: PostgreSQL setup, migration, and embedding backfill.
- `utils/`: CER and vocabulary helpers.
- `tests/`: focused regression checks and OCR diagnostics.

See [Architecture](ARCHITECTURE.md), [Document flow](COMPLETE_FLOW_DOCUMENTATION.md), [Project structure](PROJECT_STRUCTURE.md), and [Embedding plan](DUAL_EMBEDDING_PLAN.md).

## Current limitations

The active draft is stored in shared process memory. Restarting the server loses unsaved work, and separate users do not yet have isolated draft storage. Original image files remain in `uploads/`.
