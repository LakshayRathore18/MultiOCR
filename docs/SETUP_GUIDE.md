# Multi-Model OCR - Human-in-the-Loop Setup Guide

## 🚀 New Features Implemented

### Human-in-the-Loop Review System
- **Version Control**: OCR output (v1) and corrected text (v2) stored separately
- **CER Calculation**: Automatic Character Error Rate computation
- **Professional UI**: Side-by-side comparison and correction interface
- **Database Integration**: PostgreSQL storage for all document versions

## 📦 Required Dependencies

Install these packages if not already installed:

```bash
pip install python-dotenv psycopg2-binary python-Levenshtein
```

## 🗄️ Database Setup

1. **Create the database** (if not exists):
```sql
CREATE DATABASE multiocrDB;
```

2. **Create the documents table**:
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    image_path TEXT NOT NULL,
    ocr_text TEXT NOT NULL,
    corrected_text TEXT,
    cer FLOAT,
    status VARCHAR(20) DEFAULT 'ocr',  -- ocr | corrected
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔐 Security Configuration

1. Your database credentials are now stored in `.env` file
2. The `.env` file is added to `.gitignore` to prevent exposure
3. Never commit `.env` to version control

## 🎯 How It Works

### Workflow:
1. **Upload Image** → OCR Processing → Text Extraction
2. **Save to Database** → Version 1 (OCR output) stored automatically
3. **Review Button** → Opens human review interface
4. **Manual Correction** → Reviewer types actual text
5. **Save Correction** → Version 2 saved with CER calculation
6. **CER Display** → Shows accuracy metrics

### Features:
- ✅ Automatic database saving after OCR
- ✅ Review & Correct button appears after processing
- ✅ Side-by-side image and OCR output display
- ✅ Manual text correction with live CER calculation
- ✅ Version tracking (v1 = OCR, v2 = Corrected)
- ✅ Professional, responsive UI

## 🔄 Usage

1. **Start the application**:
```bash
python app.py
```

2. **Upload an image** and process with OCR

3. **Click "Review & Correct Text"** button

4. **Review the OCR output** in the left panel

5. **Type the actual text** in the right panel

6. **Click "Save Correction"** to store version 2

7. **CER is calculated** automatically and displayed

## 📊 Character Error Rate (CER)

CER measures OCR accuracy:
- **< 0.05**: Excellent accuracy 🎯
- **0.05-0.15**: Good accuracy ✅
- **0.15-0.30**: Moderate accuracy ⚠️
- **> 0.30**: Needs improvement 🔧

Formula: `CER = Levenshtein Distance / Text Length`

## 📁 Files Created/Modified

### New Files:
- `db.py` - Secure database connection with environment variables
- `cer.py` - Character Error Rate calculation
- `templates/review.html` - Human review interface
- `.env` - Environment variables (credentials)
- `.env.example` - Template for environment setup
- `.gitignore` - Protect sensitive files

### Modified Files:
- `app.py` - Added review routes and database integration
- `static/script.js` - Added review button functionality
- `static/style.css` - Enhanced styling for review UI

## 🎨 UI Features

- Professional gradient design
- Responsive layout (works on all devices)
- Real-time status messages
- Loading states and animations
- Success/error feedback
- Version badges (v1/v2)
- CER visualization

## 🔧 Troubleshooting

**Issue**: Database connection fails
- **Solution**: Check `.env` file has correct credentials
- Verify PostgreSQL is running on port 5432

**Issue**: ModuleNotFoundError for dotenv/psycopg2/Levenshtein
- **Solution**: Run `pip install python-dotenv psycopg2-binary python-Levenshtein`

**Issue**: Review button doesn't appear
- **Solution**: Ensure database connection is working and document ID is returned

## 📝 Notes

- Documents table auto-increments IDs
- `updated_at` timestamp updates on corrections
- Status changes from 'ocr' to 'corrected' after review
- Version increments from 1 to 2 after correction
- CER is NULL until corrected text is provided

## 🎉 Ready to Use!

Your OCR application now has enterprise-grade human-in-the-loop capabilities with version control and accuracy tracking!
