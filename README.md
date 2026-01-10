# 🚀 MultiOCR Setup Guide

Complete setup instructions for the Multi-Model OCR system with human-in-the-loop correction, version control, and hash-based document identity.

---

## 📋 Table of Contents

- [Installation](#installation)
- [Database Setup](#database-setup)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)

---

## 📦 Installation

### 1. Clone or Download the Repository

```bash
cd C:\CODING\MultiOCRnew
# If already downloaded, skip to next step
```

### 2. Create Virtual Environment

```bash
cd multiocr
python -m venv .venv
```

### 3. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Expected packages include:**
- `Flask` - Web framework
- `psycopg2-binary` - PostgreSQL adapter
- `paddlepaddle` / `paddleocr` - PaddleOCR engine
- `easyocr` - EasyOCR engine
- `pytesseract` - Tesseract wrapper
- `torch` / `torchvision` - PyTorch for CRAFT model
- `python-Levenshtein` - CER calculation
- `python-dotenv` - Environment management
- `Pillow` - Image processing
- And more...

---

## 🗄️ Database Setup

### 1. Start PostgreSQL Service

**Windows:**
```powershell
# Check if running
Get-Service postgresql*

# If not running, start it (adjust service name)
Start-Service postgresql-x64-15
```

**Linux:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Auto-start on boot
```

### 2. Create Database User (if needed)

Connect to PostgreSQL as admin:

```sql
-- Create user
CREATE USER postgres WITH PASSWORD 'pg1234';

-- Grant privileges
ALTER USER postgres WITH SUPERUSER;
```

### 3. Run Database Setup Script

```bash
python setup_database.py
```

**Expected output:**
```
============================================================
🗄️  MultiOCR Database Setup
============================================================
Host: localhost:5432
Database: multiocrdb
User: postgres
============================================================

✓ Database 'multiocrdb' already exists

📋 Creating tables...
  ✓ documents table created

🔍 Creating indexes...
  ✓ idx_image_hash - Hash-based lookup
  ✓ idx_parent_id - Version tracking
  ✓ idx_status - Status filtering
  ✓ idx_created_at - Time-based sorting

⚙️  Creating triggers...
  ✓ Auto-update timestamp trigger created

🔍 Verifying setup...
  ✓ Documents table accessible (0 rows)

============================================================
✅ Database setup completed successfully!
============================================================
```

### 4. Verify Database

```bash
# Connect to database
psql -U postgres -d multiocrdb

# Check tables
\dt

# View schema
\d documents

# Exit
\q
```

**Expected table schema:**
```
 Column         | Type                        | Description
----------------+-----------------------------+--------------------------------
 id             | SERIAL PRIMARY KEY          | Auto-increment ID
 image_path     | TEXT NOT NULL               | Path to uploaded image
 image_hash     | VARCHAR(64)                 | SHA256 hash for deduplication
 ocr_text       | TEXT NOT NULL               | Original OCR output (v1)
 corrected_text | TEXT                        | Human-corrected text (v2)
 cer            | FLOAT                       | Character Error Rate
 parent_id      | INTEGER                     | Reference to parent document
 version        | INTEGER DEFAULT 1           | Version number (1=OCR, 2=corrected)
 status         | VARCHAR(20)                 | Status: pending/ocr/corrected
 text_embedding | JSONB                       | For similarity search
 created_at     | TIMESTAMP                   | Creation timestamp
 updated_at     | TIMESTAMP                   | Last update timestamp
```

---

## ⚙️ Environment Configuration

### 1. Copy Environment Template

```bash
copy .env.example .env
```

### 2. Edit `.env` File

Open `.env` in a text editor and configure:

```bash
# Database Configuration
DB_NAME=your_database_name
DB_USER=postgres
DB_PASSWORD=your_actual_password_here
DB_HOST=localhost
DB_PORT=5432

# GPU Configuration
# Set to true if you have CUDA-compatible GPU
USE_GPU=false

# PaddleOCR Configuration
# Disable model download check to avoid connectivity issues
DISABLE_MODEL_SOURCE_CHECK=True
```


## 🚀 Running the Application

### 1. Start the Flask Application

```bash
python web\app.py
```

**Expected startup output:**
```
Initializing OCR models...
✓ PaddleOCR loaded successfully!
✓ EasyOCR loaded successfully!
✓ DeepSeek OCR loaded successfully!

📚 Initializing PostOCR correction module...
✅ PostOCR correction module ready for use!

✅ OCR models loaded successfully!

============================================================
🚀 Initializing CRAFT model at startup...
============================================================
✓ CRAFT model loaded successfully!

 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.37:5000
```

### 2. Access the Application

Open your web browser and navigate to:
- **Local**: http://127.0.0.1:5000
- **Network**: http://192.168.1.37:5000 (accessible from other devices on same network)

### 3. Stop the Application

Press `Ctrl+C` in the terminal to stop the server.

---

## 📖 Usage Guide

### Basic Workflow

#### 1. **Upload Image**
   - Drag & drop or click "Browse" to select an image
   - Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF
   - Maximum size: 16MB

#### 2. **Process OCR**
   - Click **"Parse Document"** button
   - System will:
     - Compute SHA256 hash of the image
     - Check if image was processed before
     - If new: Run OCR with PaddleOCR, EasyOCR, and DeepSeek
     - If duplicate: Return existing results

#### 3. **View Results**
   - **OCR Text**: Extracted text appears in the text area
   - **Visualization**: Character detection bounding boxes
   - **Metrics**: Processing time, confidence scores, line count

#### 4. **Review & Correct** (Optional)
   - Click **"Review & Correct Text"**
   - Compare OCR output (left) with corrected text (right)
   - Edit the corrected text as needed
   - Click **"Save Correction"** to create v2

#### 5. **Post-OCR Correction** (Advanced)
   - **Detect Errors**: Click to find potential OCR mistakes
   - **Auto Fix**: Automatically correct common errors using dictionary
   - **Add to Dictionary**: Save custom corrections for future use

### Advanced Features

#### Version Control
- **v1 (OCR)**: Original OCR output
- **v2 (Corrected)**: Human-corrected text
- System tracks both versions and calculates CER (Character Error Rate)

#### Hash-Based Deduplication
- Each uploaded image gets a unique SHA256 hash
- Re-uploading the same image returns cached results instantly
- No re-processing needed for duplicates

#### Character Error Rate (CER)
```
CER = Levenshtein Distance / Length of Ground Truth

• < 0.05:   Excellent 🎯
• 0.05-0.15: Good ✅
• 0.15-0.30: Moderate ⚠️
• > 0.30:    Needs Improvement 🔧
```

#### Semantic Similarity (If Enabled)
- Find similar documents based on text embeddings
- Useful for finding reference documents when correcting

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     Web Interface                        │
│                  (Flask + HTML/CSS/JS)                  │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐          ┌──────▼────────┐
│  OCR Pipeline  │          │   Database    │
│                │          │  (PostgreSQL) │
│ • PaddleOCR    │          │               │
│ • EasyOCR      │◄─────────┤ • documents   │
│ • DeepSeek     │          │ • versions    │
│ • Voting       │          │ • embeddings  │
└────────┬───────┘          └───────────────┘
         │
         │
┌────────▼───────────────────────────────────┐
│          PostOCR Correction                │
│                                            │
│ • Dictionary (360K+ words)                 │
│ • Confusion Pairs (learned patterns)       │
│ • Domain Words (Sanskrit-specific)         │
│ • Trie-based Fast Search                  │
└────────────────────────────────────────────┘
```

### Hash-Based Document Identity

```
Upload Image → Compute SHA256 Hash → Check Database
                                          ↓
                            ┌─────────────┴─────────────┐
                            ↓                           ↓
                    Hash Exists                  Hash New
                    (Return v1/v2)              (Process OCR)
                            ↓                           ↓
                    Show Existing Results        Save as v1
                                                        ↓
                                            Human Correction
                                                        ↓
                                                Save as v2
                                            (parent_id = v1.id)
```

### OCR Voting System

```
PaddleOCR ──┐
            ├──► Voting Logic ──► Final Result
EasyOCR  ───┤    (Confidence    (Deduplicated)
            │     + Similarity)
DeepSeek ───┘
```

---


## 📁 Project Structure

```
multiocr/
├── 📄 SETUP.md                    # This file
├── 📄 setup_database.py           # Database initialization script
├── 📄 requirements.txt            # Python dependencies
├── 📄 .env.example                # Environment template
├── 📄 .env                        # Your configuration (not in git)
│
├── 📁 web/                        # Flask application
│   ├── app.py                     # Main Flask app
│   ├── templates/                 # HTML templates
│   │   ├── index.html             # Main UI
│   │   └── review_new.html        # Review/correction interface
│   └── static/                    # CSS, JS, images
│       ├── style.css
│       └── script.js
│
├── 📁 ocr/                        # OCR engines
│   ├── paddle_ocr.py              # PaddleOCR implementation
│   ├── easy_ocr.py                # EasyOCR implementation
│   ├── deepseek_ocr.py            # DeepSeek OCR via Ollama
│   ├── voting.py                  # Multi-model voting
│   ├── benchmark.py               # Performance metrics
│   └── normalize.py               # Text normalization
│
├── 📁 src/                        # Core modules
│   ├── database/                  # Database utilities
│   │   ├── db.py                  # Database connection
│   │   └── migrate_db.py          # Legacy migration script
│   ├── utils/                     # Utility functions
│   │   ├── cer.py                 # CER calculation
│   │   └── image_hash.py          # SHA256 hashing
│   └── similarity/                # Semantic search (optional)
│       ├── embeddings.py
│       └── search.py
│
├── 📁 postOCR/                    # Post-correction module
│   ├── data/                      # Dictionaries and wordlists
│   │   ├── Dict.txt               # Base dictionary (360K words)
│   │   ├── learned_confusions.txt # OCR error patterns
│   │   ├── learned_domain_words.txt # Custom words
│   │   ├── scraped_samhita.txt    # Sanskrit terms (38K)
│   │   └── ccras_wordlist.txt     # CCRAS wordlist (55K)
│   └── src/                       # Correction engine
│       └── core/
│           ├── corrector.py
│           ├── dictionary.py
│           └── confusion_pairs.py
│
├── 📁 char_visualisation/         # CRAFT model for visualization
│   └── line-segmentation/
│       └── pretrained_craft/
│           └── craft_mlt_25k.pth  # Pre-trained model
│
├── 📁 uploads/                    # Uploaded images
│   └── visualizations/            # Generated visualizations
│
├── 📁 logs/                       # Application logs
└── 📁 docs/                       # Additional documentation
    ├── IMPLEMENTATION_SUMMARY.md
    ├── QUICKSTART.md
    └── ...
```

---

## 🎯 Key Features Summary

### ✅ Multi-Model OCR
- **PaddleOCR**: Chinese/English/Devanagari support
- **EasyOCR**: 80+ languages
- **DeepSeek OCR**: LLM-based OCR via Ollama
- **Voting System**: Combines results for best accuracy

### ✅ Hash-Based Deduplication
- SHA256 hashing prevents redundant processing
- Instant retrieval of previously processed documents
- Saves computation time and resources

### ✅ Version Control
- Track OCR output (v1) and corrections (v2)
- Parent-child relationships between versions
- Complete audit trail of changes

### ✅ CER Tracking
- Quantify OCR accuracy improvement
- Measure correction quality
- Identify problematic documents

### ✅ Post-OCR Correction
- 360K+ word dictionary
- Learned confusion patterns
- Domain-specific vocabulary (Sanskrit)
- Real-time error detection
- Auto-correction suggestions

### ✅ Visualization
- CRAFT-based character detection
- Bounding box visualization
- Confidence heatmaps

### ✅ Performance
- GPU acceleration (optional)
- Model caching and reuse
- Efficient database indexing
- Fast trie-based search

---

## 🚀 Quick Start Commands

```bash
# 1. Setup (one time only)
cd multiocr
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your database password
python setup_database.py

# 2. Run application (every time)
.venv\Scripts\Activate.ps1
python web\app.py

# 3. Access in browser
# http://127.0.0.1:5000
```

---


