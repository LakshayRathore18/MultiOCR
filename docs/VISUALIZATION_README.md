# Character Visualization Feature

## Overview

The character visualization feature provides detailed analysis of Devanagari text recognition by showing:
- **Character-level bounding boxes** - Each detected character highlighted
- **CRAFT heatmaps** - Character region confidence visualization
- **Line segmentation** - Detected text line boundaries
- **Combined analysis** - Multi-panel view with statistics

## Setup

### 1. Install Dependencies

Run the installation script:
```bash
install_visualization_deps.bat
```

Or manually install:
```bash
pip install matplotlib==3.10.1 scikit-image==0.24.0
```

### 2. Download CRAFT Model

The visualization uses the CRAFT (Character Region Awareness for Text detection) model.

**Download the model:**
- Download `craft_mlt_25k.pth` from: https://drive.google.com/open?id=1Jk4eGD7crsqCCg9C9VjCLkMN3ze8kutZ
- Place it at: `char_visualisation/line-segmentation/pretrained_craft/craft_mlt_25k.pth`

**File structure should be:**
```
char_visualisation/
  └── line-segmentation/
      └── pretrained_craft/
          └── craft_mlt_25k.pth  (place model file here)
```

## How It Works

### Backend Processing

When an image is uploaded:
1. The image is sent to both OCR and visualization pipelines in parallel
2. The CRAFT model detects character regions and generates heatmaps
3. Bounding boxes are computed for each character
4. Lines are detected and characters are assigned to lines
5. Four visualization images are generated and saved to `static/visualizations/`

### Frontend Display

The visualizations appear automatically after OCR processing with tabs to switch between:
- **Combined View** - Overview with statistics
- **Bounding Boxes** - Character detection boxes
- **Heatmap** - Character confidence regions
- **Line Segmentation** - Detected text lines

## Files Modified/Created

### New Files:
- `ocr/visualize.py` - Main visualization module
- `static/visualizations/` - Output directory for visualization images
- `install_visualization_deps.bat` - Dependency installer
- `VISUALIZATION_README.md` - This file

### Modified Files:
- `app.py` - Added `/visualize` endpoint
- `templates/index.html` - Added visualization display section
- `static/script.js` - Added visualization fetching and tab switching
- `static/style.css` - Added visualization styling
- `requirements.txt` - Added matplotlib and scikit-image

## API Endpoint

### POST `/visualize`

**Request:**
```json
{
  "filepath": "uploads/image.jpg"
}
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_characters": 245,
    "total_lines": 12,
    "avg_chars_per_line": 20.4,
    "image_size": "800 × 600"
  },
  "images": {
    "bounding_boxes": "/static/visualizations/image/bounding_boxes.png",
    "heatmap": "/static/visualizations/image/heatmap.png",
    "line_segmentation": "/static/visualizations/image/line_segmentation.png",
    "combined_analysis": "/static/visualizations/image/combined_analysis.png"
  }
}
```

## Usage from Python

You can also use the visualization module directly:

```python
from ocr.visualize import generate_visualization

result = generate_visualization(
    image_path='path/to/image.jpg',
    output_dir='visualization_output'
)

if result['success']:
    print(f"Detected {result['stats']['total_characters']} characters")
    print(f"Found {result['stats']['total_lines']} lines")
    print(f"Images saved to: {result['images']}")
```

## Troubleshooting

### "CRAFT model not found"
- Ensure `craft_mlt_25k.pth` is in the correct location
- Check file permissions

### "Module 'matplotlib' not found"
- Run `install_visualization_deps.bat`
- Or manually: `pip install matplotlib scikit-image`

### Visualizations not appearing
- Check browser console for errors
- Verify `/visualize` endpoint returns success
- Check `static/visualizations/` directory has write permissions

### Out of memory errors
- The CRAFT model requires ~200MB GPU memory or ~500MB RAM
- Reduce image size before uploading if needed
- Model is cached after first use for better performance

## Performance

- **First run:** ~5-10 seconds (model loading + processing)
- **Subsequent runs:** ~2-3 seconds (model cached)
- **Parallel processing:** OCR and visualization run simultaneously
- **Memory:** ~500MB additional RAM for CRAFT model

## Credits

- CRAFT model: https://github.com/clovaai/CRAFT-pytorch
- Based on research: "Character Region Awareness for Text Detection"
