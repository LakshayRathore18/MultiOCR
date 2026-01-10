def init_easy_model():
    """Initialize EasyOCR model once (for reuse)"""
    import easyocr
    import os
    import torch
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Check GPU availability
    use_gpu_env = os.getenv('USE_GPU', 'true').lower() == 'true'
    gpu_available = torch.cuda.is_available() and torch.cuda.device_count() > 0
    use_gpu = use_gpu_env and gpu_available
    
    print(f"🔍 EasyOCR GPU check: env={use_gpu_env}, available={gpu_available}, using={use_gpu}")
    
    if use_gpu_env and not gpu_available:
        print("⚠️  GPU requested but not available. Using CPU for EasyOCR.")
    
    try:
        # Initialize with explicit device setting
        ocr = easyocr.Reader(
            ['hi'], 
            gpu=use_gpu,
            verbose=True,  # Enable verbose to see what's happening
            download_enabled=True
        )
        return ocr
    except Exception as e:
        print(f"❌ EasyOCR initialization failed with GPU={use_gpu}: {e}")
        print("🔄 Retrying with CPU...")
        # Fallback to CPU
        ocr = easyocr.Reader(
            ['hi'], 
            gpu=False,
            verbose=True,
            download_enabled=True
        )
        return ocr

def run_easyocr(image_path, model=None):
    """Run EasyOCR with aggressive line grouping"""
    if model is None:
        model = init_easy_model()
    
    result = model.readtext(image_path)
    
    if not result:
        return []
    
    # Extract all detections with positions
    raw_results = []
    for bbox, text, confidence in result:
        y_pos = min(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
        y_pos_max = max(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
        x_pos = min(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
        x_pos_max = max(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
        
        text_height = y_pos_max - y_pos
        y_center = (y_pos + y_pos_max) / 2
        
        raw_results.append({
            "text": text,
            "confidence": float(confidence),
            "y_center": y_center,
            "y_pos": y_pos,
            "y_pos_max": y_pos_max,
            "x_pos": x_pos,
            "x_pos_max": x_pos_max,
            "height": text_height
        })
    
    # STEP 1: Group by Y-coordinate (cluster lines)
    # Sort by y_center first
    raw_results.sort(key=lambda x: x["y_center"])
    
    line_groups = []
    current_group = [raw_results[0]]
    
    for i in range(1, len(raw_results)):
        item = raw_results[i]
        prev_item = raw_results[i-1]
        
        # If Y-center is close, same line
        y_diff = abs(item["y_center"] - prev_item["y_center"])
        
        if y_diff < 30:  # 30px tolerance for same line
            current_group.append(item)
        else:
            line_groups.append(current_group)
            current_group = [item]
    
    line_groups.append(current_group)
    
    # STEP 2: Within each group, sort by X and merge
    merged_results = []
    
    for group in line_groups:
        # Sort by x_pos (left to right)
        group.sort(key=lambda x: x["x_pos"])
        
        # Merge all in group into one line
        merged_text = " ".join([item["text"] for item in group])
        merged_confidence = sum([item["confidence"] for item in group]) / len(group)
        
        # Boost confidence for Devanagari
        boosted_confidence = min(merged_confidence * 1.55, 0.99)
        
        merged_results.append({
            "text": merged_text,
            "confidence": boosted_confidence
        })
    
    return merged_results

# def init_easy_model():
#     """Initialize EasyOCR model once (for reuse)"""
#     import easyocr
    
#     ocr = easyocr.Reader(['hi'], gpu=True, verbose=False)
#     return ocr


# def run_easyocr(image_path, model=None):
#     """Run EasyOCR with aggressive line grouping"""
#     if model is None:
#         model = init_easy_model()
    
#     result = model.readtext(image_path)
    
#     if not result:
#         return []
    
#     # Extract all detections with positions
#     raw_results = []
#     for bbox, text, confidence in result:
#         y_pos = min(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
#         y_pos_max = max(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
#         x_pos = min(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
#         x_pos_max = max(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
        
#         text_height = y_pos_max - y_pos
#         y_center = (y_pos + y_pos_max) / 2
        
#         raw_results.append({
#             "text": text,
#             "confidence": float(confidence),
#             "y_center": y_center,
#             "y_pos": y_pos,
#             "y_pos_max": y_pos_max,
#             "x_pos": x_pos,
#             "x_pos_max": x_pos_max,
#             "height": text_height
#         })
    
#     # STEP 1: Group by Y-coordinate (cluster lines)
#     # Sort by y_center first
#     raw_results.sort(key=lambda x: x["y_center"])
    
#     line_groups = []
#     current_group = [raw_results[0]]
    
#     for i in range(1, len(raw_results)):
#         item = raw_results[i]
#         prev_item = raw_results[i-1]
        
#         # If Y-center is close, same line
#         y_diff = abs(item["y_center"] - prev_item["y_center"])
        
#         if y_diff < 40:  # 40px tolerance for same line
#             current_group.append(item)
#         else:
#             line_groups.append(current_group)
#             current_group = [item]
    
#     line_groups.append(current_group)
    
#     # Add this after line_groups creation to see what's happening:
#     for i, group in enumerate(line_groups):
#         print(f"Line {i}: {len(group)} items, y_center range: {[x['y_center'] for x in group]}")
#         for item in group:
#             print(f"  - {item['text']} @ x={item['x_pos']:.0f}")
    
#     # STEP 2: Within each group, sort by X and merge
#     merged_results = []
    
#     for group in line_groups:
#         # Sort by x_pos (left to right)
#         group.sort(key=lambda x: x["x_pos"])
        
#         # Merge all in group into one line
#         merged_text = " ".join([item["text"] for item in group])
#         merged_confidence = sum([item["confidence"] for item in group]) / len(group)
        
#         # Boost confidence for Devanagari
#         boosted_confidence = min(merged_confidence * 1.55, 0.99)
        
#         merged_results.append({
#             "text": merged_text,
#             "confidence": boosted_confidence
#         })
    
#     return merged_results