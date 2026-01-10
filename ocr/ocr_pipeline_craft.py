"""
Enhanced OCR Pipeline with CRAFT Line Segmentation
Flow: Image -> CRAFT Segmentation -> Line-by-line OCR -> Voting -> Final Result
"""

from ocr.paddle_ocr import run_paddleocr
from ocr.easy_ocr import run_easyocr
from ocr.deepseek_ocr import run_deepseek
from ocr.voting import ocr_voting
from ocr.benchmark import benchmark_ocr
from ocr.tesseract_ocr import run_tesseract
from ocr.craft_segmenter import segment_image_into_lines, init_craft_model
import os


def run_ocr_with_segmentation(image_path, mode='fast', use_segmentation=True, 
                               paddle_model=None, easy_model=None, deepseek_model=None):
    """
    Run OCR with optional CRAFT line segmentation.
    
    Args:
        image_path: Path to input image
        mode: 'fast' (PaddleOCR only), 'accurate' (PaddleOCR + EasyOCR + DeepSeek voting), or 'deepseek' (DeepSeek only)
        use_segmentation: If True, segment lines first using CRAFT
        paddle_model: Pre-initialized PaddleOCR model
        easy_model: Pre-initialized EasyOCR model
        deepseek_model: Pre-initialized DeepSeek model
    
    Returns:
        dict: {
            'results': [...],  # OCR results
            'benchmark': {...},  # Timing info
            'segmentation': {...},  # Segmentation info (if used)
            'full_text': str
        }
    """
    results = {
        'segmentation_used': use_segmentation,
        'mode': mode
    }
    
    if use_segmentation:
        print("\n🔍 Segmenting image into lines using CRAFT...")
        try:
            # Segment image into lines
            seg_result = segment_image_into_lines(image_path)
            
            results['segmentation'] = {
                'total_lines': seg_result['total_lines'],
                'line_folder': seg_result['line_folder']
            }
            
            print(f"✓ Found {seg_result['total_lines']} lines")
            
            # Process each line with OCR
            all_line_results = []
            
            for line_info in seg_result['lines']:
                line_path = line_info['path']
                line_num = line_info['line_number']
                
                print(f"  Processing line {line_num + 1}/{seg_result['total_lines']}...")
                
                if mode == 'fast':
                    # Fast mode: PaddleOCR only
                    line_result = run_paddleocr(line_path, paddle_model)
                elif mode == 'deepseek':
                    # DeepSeek mode: DeepSeek only
                    line_result = run_deepseek(line_path, deepseek_model)
                else:
                    # Accurate mode: Paddle + DeepSeek voting (EasyOCR disabled)
                    paddle_result = run_paddleocr(line_path, paddle_model)
                    # easy_result = run_easyocr(line_path, easy_model)  # Commented out: EasyOCR disabled
                    deepseek_result = run_deepseek(line_path, deepseek_model) if deepseek_model else []
                    line_result = ocr_voting(paddle_result, deepseek_results=deepseek_result)
                    
                    # Fallback to Tesseract if all fail
                    if not line_result:
                        line_result = run_tesseract(line_path)
                
                # Add line metadata
                for item in line_result:
                    item['line_number'] = line_num
                    item['source_line_path'] = line_path
                
                all_line_results.extend(line_result)
            
            results['results'] = all_line_results
            
        except Exception as e:
            print(f"⚠️  Segmentation failed: {e}")
            print("   Falling back to full-image OCR...")
            use_segmentation = False
    
    # If segmentation disabled or failed, process full image
    if not use_segmentation:
        print("\n📄 Processing full image without segmentation...")
        
        if mode == 'fast':
            # Fast mode: PaddleOCR only
            paddle_data = benchmark_ocr(lambda path: run_paddleocr(path, paddle_model), image_path)
            results['results'] = paddle_data["results"]
            results['benchmark'] = {
                'paddleocr': {
                    'time': paddle_data['time_sec'],
                    'lines': paddle_data['lines'],
                    'avg_confidence': paddle_data['avg_confidence']
                }
            }
        elif mode == 'deepseek':
            # DeepSeek mode: DeepSeek only
            deepseek_data = benchmark_ocr(lambda path: run_deepseek(path, deepseek_model), image_path)
            results['results'] = deepseek_data["results"]
            results['benchmark'] = {
                'deepseek': {
                    'time': deepseek_data['time_sec'],
                    'lines': deepseek_data['lines'],
                    'avg_confidence': deepseek_data['avg_confidence']
                }
            }
        else:
            # Accurate mode: All engines + voting
            paddle_data = benchmark_ocr(lambda path: run_paddleocr(path, paddle_model), image_path)
            easy_data = benchmark_ocr(lambda path: run_easyocr(path, easy_model), image_path)
            
            deepseek_data = None
            if deepseek_model:
                deepseek_data = benchmark_ocr(lambda path: run_deepseek(path, deepseek_model), image_path)
            
            # Apply voting (Paddle vs DeepSeek only - EasyOCR disabled)
            final_output = ocr_voting(
                paddle_data["results"],
                deepseek_results=deepseek_data["results"] if deepseek_data else None
            )
            
            # Fallback to Tesseract
            if not final_output:
                final_output = run_tesseract(image_path)
            
            results['results'] = final_output
            results['benchmark'] = {
                'paddleocr': {
                    'time': paddle_data['time_sec'],
                    'lines': paddle_data['lines'],
                    'avg_confidence': paddle_data['avg_confidence']
                },
                'easyocr': {
                    'time': easy_data['time_sec'],
                    'lines': easy_data['lines'],
                    'avg_confidence': easy_data['avg_confidence']
                }
            }
            
            if deepseek_data:
                results['benchmark']['deepseek'] = {
                    'time': deepseek_data['time_sec'],
                    'lines': deepseek_data['lines'],
                    'avg_confidence': deepseek_data['avg_confidence']
                }
    
    # Generate full text
    results['full_text'] = '\n'.join([item['text'] for item in results['results']])
    
    return results


if __name__ == "__main__":
    import sys
    from ocr.paddle_ocr import init_paddle_model
    from ocr.easy_ocr import init_easy_model
    
    if len(sys.argv) < 2:
        print("Usage: python ocr_pipeline_craft.py <image_path> [mode] [use_segmentation]")
        print("  mode: 'fast' or 'accurate' (default: fast)")
        print("  use_segmentation: 'yes' or 'no' (default: yes)")
        sys.exit(1)
    
    image_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'fast'
    use_seg = sys.argv[3].lower() != 'no' if len(sys.argv) > 3 else True
    
    # Initialize models
    print("Initializing models...")
    paddle_model = init_paddle_model()
    easy_model = init_easy_model() if mode == 'accurate' else None
    
    # Run OCR pipeline
    result = run_ocr_with_segmentation(
        image_path,
        mode=mode,
        use_segmentation=use_seg,
        paddle_model=paddle_model,
        easy_model=easy_model
    )
    
    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    
    if result.get('segmentation'):
        seg = result['segmentation']
        print(f"Lines Segmented: {seg['total_lines']}")
        print(f"Lines Folder: {seg['line_folder']}")
        print()
    
    for item in result['results']:
        line_num = item.get('line_number', '?')
        print(f"[Line {line_num}] {item['text']} (conf: {item['confidence']:.3f})")
    
    print("\n" + "="*60)
    print("FULL TEXT")
    print("="*60)
    print(result['full_text'])
    print("="*60)
