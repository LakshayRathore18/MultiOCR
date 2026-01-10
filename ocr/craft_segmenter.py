"""
CRAFT Text Line Segmentation for OCR Pipeline
Segments images into individual text lines before OCR processing
"""

import cv2
import numpy as np
from craft_text_detector import Craft
import os
from pathlib import Path
import hashlib


# Global CRAFT model instance (loaded once)
_craft_model = None


def init_craft_model():
    """Initialize CRAFT model once (for reuse across requests)"""
    global _craft_model
    if _craft_model is None:
        try:
            _craft_model = Craft(output_dir=None, crop_type="poly", cuda=True)
            print("✓ CRAFT model loaded successfully with GPU!")
        except Exception as e:
            print(f"⚠️  Warning: CRAFT GPU initialization failed, trying CPU: {e}")
            try:
                _craft_model = Craft(output_dir=None, crop_type="poly", cuda=False)
                print("✓ CRAFT model loaded successfully with CPU!")
            except Exception as e2:
                print(f"❌ CRAFT model failed to load: {e2}")
                raise
    return _craft_model


def segment_image_into_lines(image_path, output_folder=None, image_hash=None):
    """
    Segment an image into individual text lines using CRAFT.
    
    Args:
        image_path: Path to the input image
        output_folder: Base folder to save lines (default: 'uploads/lines')
        image_hash: Unique hash for this image (used for organizing)
    
    Returns:
        dict: {
            'lines': [
                {
                    'path': 'path/to/line_0.png',
                    'bbox': (x, y, w, h),
                    'line_number': 0
                },
                ...
            ],
            'total_lines': int,
            'line_folder': 'path/to/lines/folder'
        }
    """
    # Set default output folder
    if output_folder is None:
        output_folder = 'uploads/lines'
    
    # Create unique subfolder for this image using hash
    if image_hash:
        line_folder = os.path.join(output_folder, image_hash[:12])
    else:
        # Generate hash from image path
        path_hash = hashlib.md5(image_path.encode()).hexdigest()[:12]
        line_folder = os.path.join(output_folder, path_hash)
    
    os.makedirs(line_folder, exist_ok=True)
    
    # Create visualization folder early
    viz_folder = os.path.join(line_folder, 'visualizations')
    os.makedirs(viz_folder, exist_ok=True)
    
    # Load CRAFT model
    craft = init_craft_model()
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")
    
    # Preprocess image for better text detection
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Apply adaptive histogram equalization to improve contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # 3. Optional: Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    
    # Save preprocessed image for debugging
    cv2.imwrite(os.path.join(viz_folder, '0_preprocessed.png'), gray)
    
    # Detect text using CRAFT
    prediction = craft.detect_text(gray)
    
    # Get heatmaps (text regions and character boundaries)
    # CRAFT returns 'text_score_heatmap' and 'link_score_heatmap'
    text_heatmap = prediction["heatmaps"].get("text_score_heatmap")
    if text_heatmap is None:
        text_heatmap = prediction["heatmaps"].get("text")
    if text_heatmap is None:
        # Try alternative key structure
        available_keys = list(prediction["heatmaps"].keys())
        raise ValueError(f"Could not find text heatmap. Available keys: {available_keys}")
    
    text_heatmap_uint8 = (text_heatmap * 255).astype(np.uint8) if text_heatmap.max() <= 1.0 else text_heatmap.astype(np.uint8)
    
    # Get character/link heatmap if available
    char_heatmap = prediction["heatmaps"].get("link_score_heatmap")
    if char_heatmap is None:
        char_heatmap = prediction["heatmaps"].get("character")
    char_heatmap_uint8 = None
    if char_heatmap is not None:
        char_heatmap_uint8 = (char_heatmap * 255).astype(np.uint8) if char_heatmap.max() <= 1.0 else char_heatmap.astype(np.uint8)
    
    # Save text region heatmap
    text_heatmap_color = cv2.applyColorMap(text_heatmap_uint8, cv2.COLORMAP_JET)
    cv2.imwrite(os.path.join(viz_folder, '1_text_heatmap.png'), text_heatmap_color)
    cv2.imwrite(os.path.join(viz_folder, '1_text_heatmap_gray.png'), text_heatmap_uint8)
    
    # Save character heatmap if available
    if char_heatmap_uint8 is not None:
        char_heatmap_color = cv2.applyColorMap(char_heatmap_uint8, cv2.COLORMAP_JET)
        cv2.imwrite(os.path.join(viz_folder, '2_character_heatmap.png'), char_heatmap_color)
        cv2.imwrite(os.path.join(viz_folder, '2_character_heatmap_gray.png'), char_heatmap_uint8)
    
    # Threshold to create binary mask - USE LOWER THRESHOLD for better detection
    _, binary = cv2.threshold(text_heatmap_uint8, 40, 255, cv2.THRESH_BINARY)  # Lowered from 50 to 40
    
    # Ensure binary mask is single channel for findContours
    if len(binary.shape) == 3:
        binary = cv2.cvtColor(binary, cv2.COLOR_BGR2GRAY)
    
    # Apply morphological operations to separate lines better
    # 1. Dilate horizontally to connect characters in the same line
    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 1))  # Increased from 50 to 100
    dilated = cv2.dilate(binary, kernel_horizontal, iterations=2)  # Increased iterations
    
    # 2. Close small gaps
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    
    cv2.imwrite(os.path.join(viz_folder, '3_binary_mask.png'), closed)
    
    # Find contours (text regions/lines)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Get bounding boxes and filter small regions
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        # Filter: minimum width and height to avoid noise
        if w > 30 and h > 8:  # Reduced thresholds to catch smaller lines
            boxes.append((x, y, w, h))
    
    print(f"  Found {len(boxes)} line regions after filtering")
    
    # If few regions detected OR one large region, try to split into lines
    if len(boxes) <= 3 or (len(boxes) == 1 and boxes[0][3] > 80):
        print(f"  Few regions detected, attempting aggressive line splitting...")
        
        # Use the entire image or largest region
        if len(boxes) > 0:
            x, y, w, h = boxes[0] if len(boxes) == 1 else (0, 0, closed.shape[1], closed.shape[0])
        else:
            x, y, w, h = 0, 0, closed.shape[1], closed.shape[0]
            
        line_region = closed[y:y+h, x:x+w]
        
        # Compute horizontal projection to find line gaps
        h_projection = np.sum(line_region, axis=1) // 255  # Count white pixels per row
        
        # Save projection visualization
        projection_viz = np.zeros((h, 200), dtype=np.uint8)
        max_val = np.max(h_projection) if np.max(h_projection) > 0 else 1
        for i, val in enumerate(h_projection):
            bar_width = int((val / max_val) * 190)
            projection_viz[i, :bar_width] = 255
        cv2.imwrite(os.path.join(viz_folder, '3a_projection_debug.png'), projection_viz)
        
        # More aggressive gap detection
        # Lines are typically where projection is high, gaps are low
        threshold = w * 0.05  # Lower to 5% of width (was 10%)
        
        # Smooth the projection to reduce noise
        from scipy.ndimage import gaussian_filter1d
        try:
            h_projection_smooth = gaussian_filter1d(h_projection.astype(float), sigma=2)
        except:
            h_projection_smooth = h_projection.astype(float)
        
        # Find local minima (gaps between lines)
        minima_indices = []
        for i in range(5, len(h_projection_smooth) - 5):
            if h_projection_smooth[i] < threshold:
                # Check if it's a local minimum
                if (h_projection_smooth[i] <= h_projection_smooth[i-1] and 
                    h_projection_smooth[i] <= h_projection_smooth[i+1]):
                    minima_indices.append(i)
        
        print(f"  Found {len(minima_indices)} potential split points")
        
        # Cluster nearby minima
        if len(minima_indices) > 0:
            split_points = [minima_indices[0]]
            for idx in minima_indices[1:]:
                if idx - split_points[-1] > 15:  # Minimum 15px between splits
                    split_points.append(idx)
            
            print(f"  Refined to {len(split_points)} split points")
            
            # Create boxes from split points
            new_boxes = []
            last_y = 0
            
            for split_y in split_points:
                if split_y - last_y > 20:  # Minimum line height 20px
                    new_boxes.append((x, y + last_y, w, split_y - last_y))
                last_y = split_y
            
            # Add final line
            if h - last_y > 20:
                new_boxes.append((x, y + last_y, w, h - last_y))
            
            if len(new_boxes) > len(boxes):
                boxes = new_boxes
                print(f"  Split into {len(boxes)} lines using projection analysis")
        
        # Fallback: If still not enough lines, use adaptive division
        if len(boxes) <= 3:
            print(f"  Using adaptive line division...")
            # Calculate median line height from entire corpus (typically 40-70px for manuscripts)
            estimated_line_height = 55
            num_lines = max(int(h / estimated_line_height), 2)
            
            new_boxes = []
            line_height = h / num_lines
            
            for i in range(num_lines):
                line_y = int(y + (i * line_height))
                line_h = int(line_height) if i < num_lines - 1 else h - int(i * line_height)
                if line_h > 15:  # Only add if height is reasonable
                    new_boxes.append((x, line_y, w, line_h))
            
            boxes = new_boxes
            print(f"  Divided into {len(boxes)} adaptive lines (avg height: {int(line_height)}px)")
    
    # Sort top-to-bottom (reading order)
    boxes = sorted(boxes, key=lambda b: b[1])
    
    # Create visualization with bounding boxes
    img_with_boxes = img.copy()
    for i, (x, y, w, h) in enumerate(boxes):
        cv2.rectangle(img_with_boxes, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(img_with_boxes, f"L{i}", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imwrite(os.path.join(viz_folder, '4_segmented_lines.png'), img_with_boxes)
    
    # Create overlay visualization (heatmap on original image)
    heatmap_resized = cv2.resize(text_heatmap_color, (img.shape[1], img.shape[0]))
    overlay = cv2.addWeighted(img, 0.6, heatmap_resized, 0.4, 0)
    cv2.imwrite(os.path.join(viz_folder, '5_heatmap_overlay.png'), overlay)
    
    # === CHARACTER-LEVEL SEGMENTATION ===
    characters_by_line = []
    img_with_chars = img.copy()
    
    if char_heatmap_uint8 is not None:
        # Create character binary mask - USE LOWER THRESHOLD
        _, char_binary = cv2.threshold(char_heatmap_uint8, 50, 255, cv2.THRESH_BINARY)  # Changed from 100 to 50
        
        # Ensure single channel
        if len(char_binary.shape) == 3:
            char_binary = cv2.cvtColor(char_binary, cv2.COLOR_BGR2GRAY)
        
        # Apply morphological operations to better separate characters
        # Remove very small noise
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        char_binary = cv2.morphologyEx(char_binary, cv2.MORPH_OPEN, kernel_open, iterations=1)
        
        cv2.imwrite(os.path.join(viz_folder, '6_character_binary_mask.png'), char_binary)
        
        # Find character contours
        char_contours, _ = cv2.findContours(char_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        char_boxes = [cv2.boundingRect(c) for c in char_contours]
        
        # Filter out very small regions (noise) and very large regions (merged text)
        char_boxes = [(x, y, w, h) for x, y, w, h in char_boxes 
                      if 8 < w < 200 and 8 < h < 200]  # Adjusted thresholds
        
        # Sort characters left-to-right, top-to-bottom
        char_boxes = sorted(char_boxes, key=lambda b: (b[1] // 30, b[0]))  # Increased Y grouping to 30
        
        print(f"  Found {len(char_boxes)} character regions")
        
        # Draw character bounding boxes
        for idx, (x, y, w, h) in enumerate(char_boxes):
            cv2.rectangle(img_with_chars, (x, y), (x+w, y+h), (255, 0, 0), 1)  # Blue boxes
            if w > 15 and h > 15:  # Only label larger chars
                cv2.putText(img_with_chars, f"C{idx}", (x, y-2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
        
        cv2.imwrite(os.path.join(viz_folder, '7_character_segmentation.png'), img_with_chars)
    
    # Extract and save line images with character segmentation
    lines = []
    img_height, img_width = img.shape[:2]
    
    for i, (x, y, w, h) in enumerate(boxes):
        # Validate and clip coordinates to image boundaries
        x = max(0, int(x))
        y = max(0, int(y))
        w = int(w)
        h = int(h)
        
        # Ensure we don't go out of bounds
        x_end = min(x + w, img_width)
        y_end = min(y + h, img_height)
        
        # Recalculate width and height after clipping
        w = x_end - x
        h = y_end - y
        
        # Skip if resulting dimensions are too small
        if w <= 0 or h <= 0 or w < 10 or h < 5:
            print(f"  Skipping line {i}: invalid dimensions ({w}x{h})")
            continue
        
        # Extract line from original image
        line_img = img[y:y_end, x:x_end]
        
        # Verify line image is valid
        if line_img is None or line_img.size == 0:
            print(f"  Skipping line {i}: empty image after extraction")
            continue
        
        # Generate output path
        line_filename = f"line_{i:03d}.png"
        line_path = os.path.join(line_folder, line_filename)
        
        # Save line image
        try:
            cv2.imwrite(line_path, line_img)
        except Exception as e:
            print(f"  Error saving line {i}: {e}")
            continue
        
        # Find characters within this line
        line_chars = []
        if char_heatmap_uint8 is not None:
            # Create characters subfolder for this line
            line_chars_folder = os.path.join(line_folder, f"line_{i:03d}_chars")
            os.makedirs(line_chars_folder, exist_ok=True)
            
            for char_idx, (cx, cy, cw, ch) in enumerate(char_boxes):
                # Check if character is within this line
                if (cy >= y and cy + ch <= y_end and 
                    cx >= x and cx + cw <= x_end):
                    
                    # Validate character coordinates
                    cx_clip = max(0, min(cx, img_width))
                    cy_clip = max(0, min(cy, img_height))
                    cx_end = max(0, min(cx + cw, img_width))
                    cy_end_char = max(0, min(cy + ch, img_height))
                    
                    cw_clip = cx_end - cx_clip
                    ch_clip = cy_end_char - cy_clip
                    
                    # Skip if too small
                    if cw_clip <= 0 or ch_clip <= 0:
                        continue
                    
                    # Extract character image
                    char_img = img[cy_clip:cy_end_char, cx_clip:cx_end]
                    
                    # Verify character image is valid
                    if char_img is None or char_img.size == 0:
                        continue
                    
                    # Save character image
                    char_filename = f"char_{char_idx:03d}.png"
                    char_path = os.path.join(line_chars_folder, char_filename)
                    
                    try:
                        cv2.imwrite(char_path, char_img)
                        
                        line_chars.append({
                            'path': char_path,
                            'bbox': (cx, cy, cw, ch),
                            'bbox_relative': (cx - x, cy - y, cw, ch),  # Relative to line
                            'char_number': char_idx
                        })
                    except Exception as e:
                        print(f"  Error saving character {char_idx}: {e}")
        
        characters_by_line.append(line_chars)
        
        lines.append({
            'path': line_path,
            'bbox': (x, y, w, h),
            'line_number': i,
            'characters': line_chars,
            'char_count': len(line_chars)
        })
    
    return {
        'lines': lines,
        'total_lines': len(lines),
        'total_characters': sum(len(chars) for chars in characters_by_line),
        'line_folder': line_folder,
        'visualizations': {
            'text_heatmap': os.path.join(viz_folder, '1_text_heatmap.png'),
            'text_heatmap_gray': os.path.join(viz_folder, '1_text_heatmap_gray.png'),
            'character_heatmap': os.path.join(viz_folder, '2_character_heatmap.png') if char_heatmap_uint8 is not None else None,
            'character_heatmap_gray': os.path.join(viz_folder, '2_character_heatmap_gray.png') if char_heatmap_uint8 is not None else None,
            'binary_mask': os.path.join(viz_folder, '3_binary_mask.png'),
            'segmented_lines': os.path.join(viz_folder, '4_segmented_lines.png'),
            'heatmap_overlay': os.path.join(viz_folder, '5_heatmap_overlay.png'),
            'character_binary_mask': os.path.join(viz_folder, '6_character_binary_mask.png') if char_heatmap_uint8 is not None else None,
            'character_segmentation': os.path.join(viz_folder, '7_character_segmentation.png') if char_heatmap_uint8 is not None else None,
            'folder': viz_folder
        }
    }


def segment_from_bytes(image_bytes, output_folder=None, image_hash=None):
    """
    Segment an image from bytes (e.g., from file upload).
    
    Args:
        image_bytes: Raw image bytes
        output_folder: Base folder to save lines
        image_hash: Unique hash for this image
    
    Returns:
        Same as segment_image_into_lines()
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode image from bytes")
    
    # Save temporarily
    temp_path = f"/tmp/temp_{image_hash[:8] if image_hash else 'upload'}.png"
    cv2.imwrite(temp_path, img)
    
    try:
        result = segment_image_into_lines(temp_path, output_folder, image_hash)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return result


def cleanup_craft_model():
    """Cleanup CRAFT model from memory"""
    global _craft_model
    if _craft_model is not None:
        try:
            _craft_model.unload_craftnet_model()
            _craft_model.unload_refinenet_model()
            _craft_model = None
            print("✓ CRAFT model unloaded")
        except Exception as e:
            print(f"⚠️  Warning: Failed to unload CRAFT model: {e}")


if __name__ == "__main__":
    # Test the segmentation
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python craft_segmenter.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    result = segment_image_into_lines(image_path, output_folder="data/lines")
    
    print(f"\n✓ Segmented {result['total_lines']} lines")
    print(f"✓ Lines saved to: {result['line_folder']}")
    
    for line_info in result['lines']:
        print(f"  Line {line_info['line_number']}: {line_info['path']}")
