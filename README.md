# 🚀 MultiOCR

**MultiOCR** is a multi-model Optical Character Recognition (OCR) system with **hash-based document identity**, **version control**, and **human-in-the-loop post-correction**.
It combines multiple OCR engines, applies a voting strategy, and tracks accuracy improvements using **Character Error Rate (CER)**.

---

## ✨ Key Features

* 🔍 **Multi-Model OCR**
  * PaddleOCR
  * EasyOCR
  * DeepSeek OCR (LLM-based via Ollama)
  * Confidence + similarity-based voting

* 🧬 **Hash-Based Deduplication**
  * SHA256 image hashing
  * Instant retrieval for duplicate uploads
  * Zero redundant processing

* 🗂️ **Version Control**
  * v1: Raw OCR output
  * v2: Human-corrected text
  * Parent–child document tracking

* 📏 **Accuracy Tracking**
  * Character Error Rate (CER)
  * Quantifies correction quality

* ✍️ **Post-OCR Correction Engine**
  * 360K+ word dictionary
  * Learned OCR confusion pairs
  * Domain-specific vocabulary (Sanskrit)
  * Auto-fix & suggestion system

---

## 📋 Table of Contents

* [Installation](#-installation)
* [Database Schema](#-database-schema)
* [Usage Guide](#-usage-guide)
* [Architecture](#-architecture)
* [Project Structure](#-project-structure)
* [Quick Start](#-quick-start)

---

## 📦 Installation

### 0. Prerequisites - Install Ollama & DeepSeek OCR

**Install Ollama:**

1. Download Ollama from [https://ollama.ai](https://ollama.ai)
2. Install and start Ollama
3. Pull DeepSeek OCR model:

```bash
ollama pull deepseek-ocr
```

✅ Verify installation: `ollama list` should show `deepseek-ocr`

### 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd multiocr
conda create -n multiocr python=3.12 -y
conda activate multiocr
```

**Activate the environment:**

Windows PowerShell: `conda activate multiocr`
Linux/macOS: `conda activate multiocr`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

If you use the launcher scripts, activate the conda environment first so `python` and `pip` resolve to the project environment.

### 3. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` - **Only change these two lines:**

```env
DB_NAME=your_database_name
DB_PASSWORD=your_postgres_password
```

### 4. Setup Database

```bash
python src/database/setup_database.py
```

✅ **Done!** Your database is ready with all tables and indexes.

### 5. Run Application

```bash
python web/app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 🗄️ Database Schema

| Column           | Description                   |
| ---------------- | ----------------------------- |
| `image_hash`     | SHA256 hash for deduplication |
| `ocr_text`       | OCR output (v1)               |
| `corrected_text` | Human-corrected text (v2)     |
| `cer`            | Character Error Rate          |
| `parent_id`      | Version linkage               |
| `status`         | pending / ocr / corrected     |

---

## 📖 Usage Guide

1. **Upload Image**: Click "Upload Image" and select a Devanagari manuscript image
2. **View Results**: Get OCR results from multiple models:
   - PaddleOCR (Devanagari)
   - EasyOCR (Hindi)
   - DeepSeek OCR (LLM-based)
3. **Voting Result**: View consolidated text from all models
4. **Post-Correction**: Apply dictionary-based corrections
5. **Character Error Rate**: See CER metrics for quality assessment
6. **Download**: Export results as JSON or save to database

---

#### Version Control
- **v1 (OCR)**: Original OCR output
- **v2 (Corrected)**: Human-corrected text
- System tracks both versions and calculates CER (Character Error Rate)

#### Hash-Based Deduplication
- Each uploaded image gets a unique SHA256 hash
- Re-uploading the same image returns cached results instantly
---

## 🏗️ Architecture

### System Flow

```
Upload → Hash Check → OCR (PaddleOCR/EasyOCR/DeepSeek) → Voting → Post-Correction → Store
```

### Hash-Based Deduplication

- SHA256 hash computed for each uploaded image
- Duplicate detection prevents re-processing
- Version tracking (v1: OCR, v2: Corrected)

### OCR Voting

- Confidence-based character selection across models
- Similarity scoring with difflib
- Deduplicated final output

---

## 📁 Project Structure

```
multiocr/
├── web/              # Flask application
├── ocr/              # OCR engines (PaddleOCR, EasyOCR, DeepSeek)
├── postOCR/          # Dictionary & correction logic
├── similarity/       # Embeddings & semantic search
├── database/         # PostgreSQL models
├── static/           # CSS and JS assets
├── templates/        # HTML templates
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

---
---

## 🚀 Quick Start

**Prerequisite:** Install [Ollama](https://ollama.ai) and run `ollama pull deepseek-ocr`

```bash
# 1. Setup
conda create -n multiocr python=3.12 -y
conda activate multiocr  # Windows
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env: Set DB_PASSWORD and DB_NAME

# 3. Initialize
python src/database/setup_database.py

# 4. Run
python web/app.py
```

→ Open [http://127.0.0.1:5000](http://127.0.0.1:5000)





