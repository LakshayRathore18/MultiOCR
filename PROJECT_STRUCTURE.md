# Project structure

Paths below are relative to the application directory containing `requirements.txt`.

| Path | Purpose |
| --- | --- |
| `web/app.py` | FastAPI routes, active drafts, review/save orchestration |
| `web/templates/index.html` | Upload, OCR output, and home reference cards |
| `web/templates/review_new.html` | Original image/text, correction tools, and saved references |
| `web/static/style.css` | Home styling |
| `web/static/review_new.css` | Review styling |
| `web/static/script.js` | Upload and OCR processing interactions |
| `web/static/document_status.js` | Original OCR, saved correction, and last-edited display |
| `web/static/similar_documents.js` | Paired reference cards, copy, loading/retry, and expansion |
| `ocr/paddle_ocr.py` | PaddleOCR adapter |
| `ocr/easy_ocr.py` | EasyOCR adapter |
| `ocr/deepseek_ocr.py` | Ollama-backed DeepSeek adapter |
| `ocr/voting.py` | Combine OCR results |
| `ocr/benchmark.py` | Processing measurements |
| `ocr/normalize.py` | Normalize and validate text |
| `ocr/devanagari_unicode.py` | Devanagari checks |
| `correction/` | Dictionary, trie, edit distance, confusion-pair logic, and tests |
| `postocr_integration.py` | Connect correction logic with web routes |
| `similarity/embeddings.py` | Lazy model loading and text encoding |
| `similarity/search.py` | Compare raw queries with both stored text vectors |
| `database/db.py` | PostgreSQL connection configuration |
| `database/setup_database.py` | Create a new database and schema |
| `database/migrate_db.py` | Upgrade existing schema and remove unused metadata |
| `database/backfill_embeddings.py` | Rebuild both vectors from stored source text |
| `utils/cer.py` | Character Error Rate |
| `utils/build_vocab.py` | Vocabulary helper |
| `scripts/` | Database diagnostics and data import/export helpers |
| `deployment/OCR_pipeline.py` | Standalone OCR pipeline |
| `start.ps1` | Start the web server using the active environment |
| `tests/test_dual_embeddings.py` | Save, search, schema, and template regressions |
| `tests/test_similar_documents.cjs` | Browser reference interaction tests |
| `tests/test_document_status.cjs` | Save-information rendering tests |
| `archived/` | Historical scraping and voting experiments |

## Configuration and generated files

- `.env.example` documents environment variables; put local credentials in `.env`.
- `requirements.txt` lists dependencies.
- `uploads/` stores images; `logs/` contains runtime logs.
- Python environments and bytecode caches are generated local files.
- The active draft is held in server process memory, while saved text lives in PostgreSQL.

## Imports

Use root-package imports:

```python
from database.db import get_db
from utils.cer import compute_cer
from similarity.search import find_similar_documents
```

## Other guides

- [README](README.md): setup, running, and usage.
- [Architecture](ARCHITECTURE.md): components and storage boundaries.
- [Complete flow](COMPLETE_FLOW_DOCUMENTATION.md): upload, OCR, search, review, and save.
- [Embedding plan](DUAL_EMBEDDING_PLAN.md): dual-text storage and search behavior.
