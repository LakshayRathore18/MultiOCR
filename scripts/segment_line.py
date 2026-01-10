import cv2
import numpy as np
from craft_text_detector import Craft
import os
from pathlib import Path


def segment_lines(image_input, output_dir="data/lines", save_lines=True):
    """
    Segment an image into text lines using CRAFT text detector.
    
    Args:
        image_input: Either a file path (str) or numpy array (image)
        output_dir: Directory to save segmented lines (default: "data/lines")
        save_lines: Whether to save lines to disk (default: True)
    
    Returns:
        list: List of tuples [(line_image, bbox), ...] where bbox is (x, y, w, h)
    """
    # Initialize CRAFT model
    craft = Craft(output_dir=None, crop_type="poly", cuda=True)
    
    # Load image
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        if img is None:
            raise ValueError(f"Could not load image from {image_input}")
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        raise ValueError("image_input must be either a file path or numpy array")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect text using CRAFT
    prediction = craft.detect_text(gray)
    
    # Get heatmap and convert to binary
    heatmap = prediction["heatmaps"]["text"]
    heatmap = (heatmap * 255).astype(np.uint8)
    
    _, binary = cv2.threshold(heatmap, 100, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Get bounding boxes
    boxes = [cv2.boundingRect(c) for c in contours]
    
    # Sort top-to-bottom
    boxes = sorted(boxes, key=lambda b: b[1])
    
    # Extract line images
    lines = []
    for i, (x, y, w, h) in enumerate(boxes):
        line = img[y:y+h, x:x+w]
        lines.append((line, (x, y, w, h)))
        
        # Save if requested
        if save_lines:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"line_{i}.png")
            cv2.imwrite(output_path, line)
    
    # Cleanup models
    craft.unload_craftnet_model()
    craft.unload_refinenet_model()
    
    return lines


def segment_lines_from_upload(image_bytes, output_dir="data/lines", save_lines=True):
    """
    Segment an image from uploaded bytes into text lines.
    
    Args:
        image_bytes: Raw image bytes (e.g., from file upload)
        output_dir: Directory to save segmented lines
        save_lines: Whether to save lines to disk
    
    Returns:
        list: List of tuples [(line_image, bbox), ...]
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode image from bytes")
    
    return segment_lines(img, output_dir, save_lines)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python segment_line.py <image_path> [output_dir]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/lines"
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    print(f"Segmenting lines from: {image_path}")
    lines = segment_lines(image_path, output_dir=output_dir, save_lines=True)
    print(f"Extracted {len(lines)} lines")
    print(f"Lines saved to: {output_dir}")
