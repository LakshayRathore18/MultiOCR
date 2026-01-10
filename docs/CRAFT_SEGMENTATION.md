# CRAFT Line Segmentation Integration Guide

## Overview
Your OCR pipeline now supports **CRAFT text line segmentation** which segments images into individual lines before OCR processing. This can improve accuracy for documents with multiple text lines.

## Flow Diagram

```
User Upload Image
       ↓
   [CRAFT Segmentation] (Optional)
       ↓
  Line Images Stored in: uploads/lines/{image_hash}/
       ↓
   [OCR Processing]
   - Fast Mode: PaddleOCR only (per line)
   - Accurate Mode: PaddleOCR + EasyOCR + Voting (per line)
       ↓
   [Results Combined]
       ↓
  Full Text Output
```

## File Structure

### Created Files
1. **ocr/craft_segmenter.py** - Core segmentation logic
2. **ocr/ocr_pipeline_craft.py** - Standalone pipeline with segmentation
3. **scripts/segment_line.py** - CLI tool for testing segmentation

### Modified Files
1. **web/app.py** - Added CRAFT integration to web interface
2. **ocr/easy_ocr.py** - Enabled GPU usage
3. **requirements.txt** - Added craft_text_detector and gdown

## Usage

### 1. Web Interface (Flask App)

Send POST request to `/process` with:

```json
{
  "filepath": "uploads/image.jpg",
  "mode": "fast",  // or "accurate"
  "use_segmentation": true,  // Enable CRAFT segmentation
  "image_hash": "abc123..."
}
```

**Response includes:**
```json
{
  "success": true,
  "segmentation": {
    "total_lines": 15,
    "line_folder": "uploads/lines/abc123456789",
    "visualizations": {
      "text_heatmap": "uploads/lines/.../visualizations/1_text_heatmap.png",
      "character_heatmap": "uploads/lines/.../visualizations/2_character_heatmap.png",
      "binary_mask": "uploads/lines/.../visualizations/3_binary_mask.png",
      "segmented_lines": "uploads/lines/.../visualizations/4_segmented_lines.png",
      "heatmap_overlay": "uploads/lines/.../visualizations/5_heatmap_overlay.png",
      "folder": "uploads/lines/abc123456789/visualizations"
    }
  },
  "text": [
    {
      "text": "नमस्ते",
      "confidence": 0.95,
      "line_number": 0
    },
    ...
  ],
  "full_text": "..."
}
```

### Viewing Visualizations via API

Access visualization images:
```
GET /visualizations/{hash}/visualizations/4_segmented_lines.png
```

### 2. Standalone Pipeline (CLI)

```bash
python ocr/ocr_pipeline_craft.py image.jpg fast yes
```

Arguments:
- `image.jpg` - Path to image
- `fast` - Mode (fast/accurate)
- `yes` - Use segmentation (yes/no)

### 3. Direct Segmentation (Testing)

```bash
python scripts/segment_line.py image.jpg output/lines
```

### 4. Test with Visualizations

```bash
python test_craft_viz.py image.jpg
```

This will show you:
- All heatmap paths
- Segmentation results
- Processing pipeline visualization
- Direct links to open visualization folder

**Output includes:**
- Text region heatmaps (color & grayscale)
- Character-level heatmaps
- Binary masks
- Bounding boxes on original image
- Overlay visualizations

## Where Lines Are Stored

**Location:** `uploads/lines/{image_hash}/`

Example structure:
```
uploads/
  lines/
    abc123456789/
      line_000.png          ← Segmented line images
      line_001.png
      line_002.png
      ...
      visualizations/       ← NEW: All heatmaps and processing steps
        1_text_heatmap.png          (Text regions - color heatmap)
        1_text_heatmap_gray.png     (Text regions - grayscale)
        2_character_heatmap.png     (Character boundaries - color)
        2_character_heatmap_gray.png (Character boundaries - grayscale)
        3_binary_mask.png           (Thresholded binary mask)
        4_segmented_lines.png       (Bounding boxes on original image)
        5_heatmap_overlay.png       (Heatmap overlaid on image)
```

Each segmented line is saved with:
- Sequential numbering (line_000, line_001, ...)
- Original image quality
- Stored under a unique hash folder per image

### Visualization Files Explained

1. **Text Heatmap** - Shows where CRAFT detected text regions (red = high confidence, blue = low)
2. **Character Heatmap** - Shows character-level boundaries within text regions
3. **Binary Mask** - Thresholded version used to find contours
4. **Segmented Lines** - Original image with green bounding boxes and line numbers
5. **Heatmap Overlay** - Text heatmap blended with original image for context

## Benefits

### With CRAFT Segmentation:
✅ Better accuracy for multi-line documents
✅ Each line processed independently
✅ Lines sorted top-to-bottom automatically
✅ GPU acceleration available
✅ Reusable line images for debugging

### Without Segmentation (Original):
✅ Faster processing
✅ Works with any image
✅ No extra storage needed

## Configuration

### Enable/Disable GPU for CRAFT

In `ocr/craft_segmenter.py`:
```python
# GPU enabled (default)
_craft_model = Craft(output_dir=None, crop_type="poly", cuda=True)

# CPU only
_craft_model = Craft(output_dir=None, crop_type="poly", cuda=False)
```

### Frontend Integration

Add a checkbox in your UI:
```html
<input type="checkbox" id="useSegmentation" name="useSegmentation">
<label>Enable Line Segmentation (CRAFT)</label>
```

Then in JavaScript:
```javascript
const use_segmentation = document.getElementById('useSegmentation').checked;

fetch('/process', {
  method: 'POST',
  body: JSON.stringify({
    filepath: filepath,
    mode: mode,
    use_segmentation: use_segmentation,  // Pass to backend
    image_hash: image_hash
  })
});
```

## Cleanup

Lines are stored permanently. To clean up old lines:

```bash
# Remove all segmented lines
rm -rf uploads/lines/*

# Remove lines for specific hash
rm -rf uploads/lines/abc123456789/
```

## Troubleshooting

### CRAFT fails to load
- Check if `craft_text_detector` and `gdown` are installed
- Verify GPU is available: `python -c "import torch; print(torch.cuda.is_available())"`
- Falls back to CPU if GPU unavailable
- Falls back to full-image OCR if segmentation fails

### No lines detected
- Image may not have clear text regions
- Try adjusting threshold in `craft_segmenter.py` line 87:
  ```python
  _, binary = cv2.threshold(heatmap, 100, 255, cv2.THRESH_BINARY)
  # Try lower value like 50 or 80
  ```

### Lines in wrong order
- CRAFT sorts top-to-bottom by default
- For multi-column documents, may need custom sorting logic

## Performance Notes

- **Segmentation time:** ~1-3 seconds per page (GPU)
- **Memory usage:** ~2GB VRAM (GPU mode)
- **Storage:** ~100-500KB per line image
- **Recommended for:** Documents with 5+ text lines

## Next Steps

1. Test segmentation with your images
2. Add UI checkbox for user control
3. Monitor storage usage in `uploads/lines/`
4. Optionally add cleanup job for old lines
