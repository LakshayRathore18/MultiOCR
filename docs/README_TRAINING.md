# OCR Correction Model Training Guide

## 🎯 Overview

This training pipeline learns to automatically correct OCR errors using your training data from PostgreSQL database.

## 📋 Quick Start

### 1. **Prepare Data**
```bash
# Export from database to train.json
python scripts\export_train_json.py
```

### 2. **Build Vocabulary**
```bash
python build_vocab.py
```
**Output:** Creates `vocab.json` with all unique characters

### 3. **Train Model**
```bash
python train.py
```
**What happens:**
- Splits data into 90% train, 10% validation
- Trains Transformer model on GPU (if available)
- Saves checkpoints in `checkpoints/` directory
- Logs to TensorBoard in `logs/` directory

**Training Progress:**
- Watch terminal for epoch updates and loss values
- Lower validation loss = better model

### 4. **Monitor Training (Optional)**
```bash
tensorboard --logdir=logs
```
Open browser to http://localhost:6006 to see:
- Training/validation loss curves
- Learning rate changes
- Model performance over time

## 🔍 See Results

### **Quick Test (3 samples)**
```bash
python test_model.py checkpoints\ocr-correction-epoch=XX-val_loss=X.XXXX.ckpt
```
Shows side-by-side comparison of OCR input, model output, and expected output.

### **Full Evaluation (with metrics)**
```bash
python evaluate.py checkpoints\ocr-correction-epoch=XX-val_loss=X.XXXX.ckpt 10
```
Shows for each sample:
- ✅ Original OCR text
- ✅ Model's corrected text
- ✅ Ground truth
- ✅ Character Error Rate (CER)
- ✅ Improvement percentage

**Output Example:**
```
Sample 1/10
=================================================
OCR Input (Original):
श्रीभगवानुवाच । पश्य में पार्थ रुूपाणि...

Model Prediction:
श्रीभगवानुवाच । पश्य मे पार्थ रूपाणि...

Ground Truth:
श्रीभगवानुवाच । पश्य मे पार्थ रूपाणि...

Metrics:
  Original CER: 15.2% (OCR vs Ground Truth)
  Model CER:    3.4% (Prediction vs Ground Truth)
  ✓ Improvement: 77.6%
```

### **Interactive Testing**
```bash
python infer.py checkpoints\best.ckpt
```
Type any OCR text and see corrected output in real-time!

## 📊 Where to Find Results

| What | Where | Description |
|------|-------|-------------|
| **Model Checkpoints** | `checkpoints/` | Saved models (`.ckpt` files) |
| **Training Logs** | `logs/` | TensorBoard logs |
| **Vocabulary** | `vocab.json` | Character mappings |
| **Config** | `checkpoints/config.json` | Training configuration |
| **Training Data** | `train.json` | OCR + corrected text pairs |

## 📈 Understanding Metrics

### **Character Error Rate (CER)**
- **< 5%** = Excellent ✅
- **5-10%** = Good ✅
- **10-20%** = Acceptable ⚠️
- **> 20%** = Needs improvement ❌

### **Validation Loss**
- Should decrease over epochs
- If increasing → model is overfitting
- Best checkpoint = lowest validation loss

## 🎨 Model Architecture

```
Input (OCR Text) 
    ↓
[Embedding + Positional Encoding]
    ↓
[Transformer Encoder] (4 layers, 8 heads)
    ↓
[Transformer Decoder] (4 layers, 8 heads)
    ↓
[Linear Layer → Vocabulary]
    ↓
Output (Corrected Text)
```

## 🚀 Training Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Batch Size | 16 | Samples per training step |
| Learning Rate | 0.001 | Initial learning rate |
| Max Epochs | 100 | Maximum training epochs |
| Early Stopping | 10 epochs | Stop if no improvement |
| Validation Split | 10% | Data for validation |
| Model Dim | 256 | Embedding dimensions |
| Attention Heads | 8 | Multi-head attention |
| Encoder Layers | 4 | Transformer encoder depth |
| Decoder Layers | 4 | Transformer decoder depth |

## 🔄 Using Trained Model

### In Python Scripts
```python
from infer import OCRCorrector

# Load model
corrector = OCRCorrector("checkpoints/best.ckpt")

# Correct single text
corrected = corrector.correct("श्रीभगवानुवाच")

# Correct multiple texts
texts = ["text1", "text2", "text3"]
results = corrector.correct_batch(texts)
```

### In Your OCR Pipeline
Integrate into `OCR_pipeline.py` or `app.py` to automatically correct OCR output.

## 📝 Files Created

1. **build_vocab.py** - Build character vocabulary
2. **dataset.py** - PyTorch dataset for loading data
3. **model.py** - Transformer model architecture
4. **train.py** - Training script
5. **infer.py** - Inference/prediction script
6. **evaluate.py** - Evaluation with metrics
7. **test_model.py** - Quick testing script

## ❓ Troubleshooting

### "vocab.json not found"
→ Run `python build_vocab.py` first

### "No GPU available"
→ Training will use CPU (slower but works)

### "CUDA out of memory"
→ Reduce batch_size in train.py (line 20)

### Model not improving
→ Train longer, add more data, or adjust hyperparameters

## 🎓 Next Steps

1. ✅ Train model: `python train.py`
2. ✅ Test it: `python test_model.py checkpoints/latest.ckpt`
3. ✅ Evaluate: `python evaluate.py checkpoints/latest.ckpt`
4. ✅ Integrate into OCR pipeline
5. ✅ Add more training data from database
6. ✅ Retrain to improve accuracy
