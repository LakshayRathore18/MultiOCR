# CRAFT Heatmap & Character Segmentation - Quick Reference

## Yes! CRAFT Does Both:

### ✅ Text Region Detection (Heatmap)
- Detects where text regions are located
- Provides confidence scores per pixel
- Saved as `1_text_heatmap.png`

### ✅ Character-Level Segmentation (Heatmap) 
- Detects individual character boundaries within text
- Provides character affinity map
- Saved as `2_character_heatmap.png`

## What Gets Saved Automatically

Every time you run CRAFT segmentation, these files are created:

```
uploads/lines/{image_hash}/
  ├── line_000.png, line_001.png, ...     ← Individual line images
  └── visualizations/
      ├── 1_text_heatmap.png               ← Text regions (red = text detected)
      ├── 1_text_heatmap_gray.png         ← Same, grayscale
      ├── 2_character_heatmap.png          ← Character boundaries
      ├── 2_character_heatmap_gray.png    ← Same, grayscale
      ├── 3_binary_mask.png                ← Thresholded mask used for contours
      ├── 4_segmented_lines.png            ← Bounding boxes with line numbers
      └── 5_heatmap_overlay.png            ← Heatmap blended with original image
```

## Quick Test

### Command Line
```bash
python test_craft_viz.py path/to/your/image.jpg
```

This will:
1. Segment the image
2. Generate all heatmaps and visualizations
3. Print paths to all generated files
4. Show you where to view them

### Via Web API

**Request:**
```javascript
fetch('/process', {
  method: 'POST',
  body: JSON.stringify({
    filepath: "uploads/image.jpg",
    use_segmentation: true,
    mode: "fast"
  })
})
```

**Response includes:**
```json
{
  "segmentation": {
    "visualizations": {
      "text_heatmap": "path/to/1_text_heatmap.png",
      "character_heatmap": "path/to/2_character_heatmap.png",
      "segmented_lines": "path/to/4_segmented_lines.png",
      "heatmap_overlay": "path/to/5_heatmap_overlay.png",
      "folder": "path/to/visualizations/"
    }
  }
}
```

**View images:**
```
http://localhost:5000/visualizations/{hash}/visualizations/4_segmented_lines.png
```

## Understanding the Heatmaps

### Text Heatmap (1_text_heatmap.png)
- **Purpose:** Shows text region detection confidence
- **Colors:** 
  - Red/Orange = High confidence text region
  - Yellow/Green = Medium confidence
  - Blue = Low confidence / no text
- **Use:** Verify CRAFT is detecting your text regions correctly

### Character Heatmap (2_character_heatmap.png)
- **Purpose:** Shows character boundaries within text
- **Colors:** Similar scale (red = character boundary)
- **Use:** See if CRAFT detected individual characters
- **Note:** More detailed than text heatmap

### Binary Mask (3_binary_mask.png)
- **Purpose:** Thresholded version of text heatmap
- **Colors:** White = text region, Black = background
- **Use:** Shows exactly what regions are extracted as lines

### Segmented Lines (4_segmented_lines.png) ⭐ Most Useful
- **Purpose:** Shows final line segmentation on original image
- **Visual:** Green bounding boxes with line numbers (L0, L1, L2...)
- **Use:** Verify line detection accuracy and reading order

### Heatmap Overlay (5_heatmap_overlay.png)
- **Purpose:** Text heatmap blended with original image
- **Visual:** 60% original image + 40% heatmap
- **Use:** See detection confidence in context of actual text

## Example Output

After running `python test_craft_viz.py myimage.jpg`:

```
======================================================================
CRAFT Text Line Segmentation with Visualizations
======================================================================

Processing: myimage.jpg

✓ Segmentation Complete!
  Total lines found: 12
  Lines saved to: data/test_segmentation/a1b2c3d4e5f6

======================================================================
VISUALIZATION FILES
======================================================================

📊 HEATMAPS:
  1. Text Region Heatmap (Color):     data/.../1_text_heatmap.png
  2. Text Region Heatmap (Grayscale): data/.../1_text_heatmap_gray.png
  3. Character Heatmap (Color):       data/.../2_character_heatmap.png
  4. Character Heatmap (Grayscale):   data/.../2_character_heatmap_gray.png

🎯 PROCESSING STEPS:
  5. Binary Threshold Mask:           data/.../3_binary_mask.png

📦 SEGMENTATION RESULTS:
  6. Lines with Bounding Boxes:       data/.../4_segmented_lines.png
  7. Heatmap Overlay on Original:     data/.../5_heatmap_overlay.png
```

## Troubleshooting

### "Character heatmap not available"
- Some CRAFT models don't output character affinity maps
- Text region heatmap is still available
- Line segmentation still works normally

### Heatmap looks wrong
- Try adjusting threshold in `craft_segmenter.py` line 93:
  ```python
  _, binary = cv2.threshold(text_heatmap_uint8, 100, 255, cv2.THRESH_BINARY)
  # Try: 50 (more sensitive), 150 (less sensitive)
  ```

### Lines not detected
- Check `4_segmented_lines.png` to see what was detected
- View `1_text_heatmap.png` - if no red regions, CRAFT didn't detect text
- Try different image preprocessing (contrast, brightness)

## Integration with Your App

The visualizations are automatically generated and included in the API response. To show them in your UI:

```javascript
if (response.segmentation?.visualizations) {
  const viz = response.segmentation.visualizations;
  
  // Show the most useful visualization
  document.getElementById('segmentedView').src = 
    '/visualizations/' + viz.segmented_lines.split('uploads/lines/')[1];
  
  // Or show heatmap overlay
  document.getElementById('heatmapView').src = 
    '/visualizations/' + viz.heatmap_overlay.split('uploads/lines/')[1];
}
```

---

**Bottom Line:** CRAFT generates both text region heatmaps AND character-level heatmaps, plus 5 different visualizations to help you understand and debug the segmentation process. All are saved automatically! 🎉
