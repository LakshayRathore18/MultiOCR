# Project Structure Documentation

This document explains the purpose of each folder and file in the MultiOCR project.

## Root Level Files

### Configuration Files
- **`.env`** - Environment variables for local development (API keys, database URLs, model paths)
- **`.env.example`** - Template for environment variables (should be committed to git)
- **`.gitignore`** - Specifies files/directories to ignore in git (venv, uploads, logs, etc.)
- **`requirements.txt`** - Python dependencies for the project

### Documentation
- **`README.md`** - Project overview, installation instructions, and basic usage
- **`ARCHITECTURE.md`** - High-level architecture documentation
- **`COMPLETE_FLOW_DOCUMENTATION.md`** - Detailed workflow documentation
- **`PROJECT_STRUCTURE.md`** - This file - project structure documentation

### Integration Files
- **`postocr_integration.py`** - Main integration point for correction module (bridges OCR results with text correction)

### Startup Scripts
- **`start.ps1`** - PowerShell script to start the web application

---

## `/multiocr/` Directory

### `/ocr/` - OCR Engine Implementations
**Purpose**: Contains different OCR engine implementations and utilities

- **`paddle_ocr.py`** - PaddleOCR engine wrapper (fast, good for Devanagari)
- **`easy_ocr.py`** - EasyOCR engine wrapper (multi-language support)
- **`deepseek_ocr.py`** - DeepSeek OCR engine wrapper (AI-based OCR)
- **`voting.py`** - Voting mechanism to combine results from multiple OCR engines
- **`benchmark.py`** - Benchmarking utility to measure OCR performance (time, confidence)
- **`normalize.py`** - Text normalization utilities for OCR output
- **`devanagari_unicode.py`** - Devanagari-specific Unicode handling and validation

### `/correction/` - Text Correction Module
**Purpose**: Text correction module using learned confusion pairs and dictionary

- **`corrector.py`** - Main text correction engine using trie-based dictionary matching
- **`confusion_pairs.py`** - Manages learned OCR error patterns (e.g., '0' -> 'O')
- **`dictionary.py`** - Dictionary management for valid word lookup
- **`edit_distance.py`** - Levenshtein distance calculation for similarity
- **`lcs.py`** - Longest Common Subsequence algorithm for text alignment
- **`file_handler.py`** - File I/O utilities for correction module

#### `/correction/data/` - Dictionary Data
**Purpose**: Stores dictionary data and learned corrections

#### `/correction/tests/` - Correction Tests
**Purpose**: Unit tests for correction module

### `/database/` - Database Management
**Purpose**: Database connection and schema management

- **`db.py`** - Database connection utilities
- **`setup_database.py`** - Database schema creation and initialization
- **`migrate_db.py`** - Database migration scripts

### `/utils/` - Utility Functions
**Purpose**: Shared utility functions

- **`cer.py`** - Character Error Rate calculation
- **`image_hash.py`** - Image hashing for duplicate detection
- **`build_vocab.py`** - Vocabulary building for ML models

### `/similarity/` - Semantic Search
**Purpose**: Document similarity search using embeddings

- **`embeddings.py`** - Text embedding generation (for semantic similarity)
- **`search.py`** - Similar document search functionality

### `/web/` - Web Application
**Purpose**: Flask web interface for OCR processing

#### `/web/app.py` - Main Flask Application
- Routes for upload, processing, review, correction
- Session management
- Database integration

#### `/web/templates/` - HTML Templates
- **`index.html`** - Main upload and processing interface
- **`review_new.html`** - Human-in-the-loop review interface for corrections

#### `/web/static/` - Static Assets
- **`style.css`** - Main stylesheet for index.html
- **`review_new.css`** - Stylesheet for review interface
- **`script.js`** - Frontend JavaScript for upload, processing, and correction

### `/scripts/` - Utility Scripts
**Purpose**: Maintenance and utility scripts

- **`check_db.py`** - Database health check script
- **`convert_parquet_to_json.py`** - Convert parquet data to JSON format
- **`export_train_json.py`** - Export training data to JSON
- **`fix_keys.py`** - Fix database keys/data issues
- **`install_similarity.bat`** - Install similarity search dependencies

### `/deployment/` - Deployment Files
**Purpose**: Deployment-related scripts and configurations

- **`OCR_pipeline.py`** - OCR pipeline for deployment
- **`start.ps1`** - PowerShell startup script

### `/tests/` - Test Suite
**Purpose**: Integration and unit tests

- **`test_ocr.py`** - OCR engine tests
- **`test_devanagari.py`** - Devanagari-specific tests
- **`test_hash_system.py`** - Image hash system tests
- **`debug_ocr.py`** - OCR debugging utilities

### `/archived/` - Archived Code
**Purpose**: Code that is no longer used but kept for reference

- **`scraping/`** - Dictionary building scripts (archived after dictionary was completed)

### `/logs/` - Log Files
**Purpose**: Application logs (OCR processing, errors, performance)

### `/uploads/` - Uploaded Files
**Purpose**: Temporary storage for uploaded images (should be cleaned periodically)

### `/__pycache__/` - Python Cache
**Purpose**: Compiled Python bytecode (auto-generated, should be in .gitignore)

### `/.venv/` - Virtual Environment
**Purpose**: Python virtual environment (auto-generated, should be in .gitignore)

---

## Recent Restructuring Changes

The following changes were made to clean up the project structure:

### Removed:
- **`/src/core/`** - Custom ML training files (not used in current workflow)
- **`/src/`** - Empty after moving database and utils
- **`/postOCR/scraping/`** - Archived to `/archived/scraping/` (dictionary building scripts)
- **Duplicate startup scripts** - Removed `start.bat`, `stop.bat`, `START_APP.bat`, `STOP_APP.bat`

### Renamed:
- **`/postOCR/`** → **`/correction/`** - Clearer naming for text correction module

### Moved:
- **`/src/database/`** → **`/database/`** - Moved to root level for easier access
- **`/src/utils/`** → **`/utils/`** - Moved to root level for easier access

---

## File Dependency Map

### Critical Files (Cannot Remove):
- `postocr_integration.py` - Bridges OCR with correction
- `web/app.py` - Main application
- `ocr/*.py` - OCR engines
- `correction/src/core/*.py` - Correction logic
- `database/db.py` - Database connection
- `utils/*.py` - Utility functions

### Optional Files (Can Archive):
- `archived/scraping/*.py` - Dictionary building (if dictionary is complete)
- `tests/debug_*.py` - Debug scripts

### Generated Files (Should Not Commit):
- `__pycache__/`
- `.venv/`
- `uploads/`
- `logs/`
- `.env` (use .env.example instead)

---

## Import Paths After Restructuring

### Updated Import Paths:
- `from src.database.db import get_db` → `from database.db import get_db`
- `from src.utils.cer import compute_cer` → `from utils.cer import compute_cer`
- `from src.utils.image_hash import compute_image_hash` → `from utils.image_hash import compute_image_hash`
- `from postOCR.src.core.corrector import OCRCorrector` → `from correction.corrector import OCRCorrector`

### Files Updated:
- `postocr_integration.py` - Updated correction module paths
- `web/app.py` - Updated database and utils imports
- `tests/test_hash_system.py` - Updated database and utils imports
- `similarity/search.py` - Updated database import
- `database/migrate_db.py` - Updated database import
- `scripts/export_train_json.py` - Updated database import
