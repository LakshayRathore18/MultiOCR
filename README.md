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

* 🖼️ **Visualization**
  * CRAFT-based character/line detection
  * Bounding boxes & overlays

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

### 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd multiocr
python -m venv .venv
```

**Activate virtual environment:**

Windows: `.venv\Scripts\Activate.ps1`  
Linux/macOS: `source .venv/bin/activate`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` - **Only change these two lines:**

```env
DB_NAME=multiocrdb
DB_PASSWORD=your_postgres_password
```

### 4. Setup Database

```bash
python setup_database.py
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
6. **Visualizations**: View character detection bounding boxes
7. **Download**: Export results as JSON or save to database

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
├── static/           # CSS, JS, visualizations
├── templates/        # HTML templates
├── char_visualisation/  # CRAFT character detection
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

---
---

## 🚀 Quick Start

```bash
# 1. Setup
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env: Set DB_PASSWORD=your_password

# 3. Initialize
python setup_database.py

# 4. Run
python web/app.py
```

→ Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📚 Documentation

- [SETUP.md](SETUP.md) - Detailed setup guide with troubleshooting
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Fast-track guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design details
- [docs/TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md) - Model training instructions

---

## 📊 Status

- ✅ **Actively developed** - Regular updates and improvements
- 🔬 **Research & production** - Used in both research workflows and production pipelines
- 🔧 **Extensible** - Easy to add new OCR engines or post-processors

---

## 🤝 Contributing

Contributions welcome! Please ensure:
- Code follows existing patterns
- Tests pass
- Documentation updated

---

## 📄 License

MIT License - See LICENSE file for details

---

**Note**: See [SETUP.md](SETUP.md) for comprehensive setup instructions including troubleshooting, verification steps, and detailed configuration options.


