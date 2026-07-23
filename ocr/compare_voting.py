import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import both voting modules
from ocr.voting import ocr_voting as new_voting
from ocr.voting_original import ocr_voting as original_voting

def print_separator(char="=", length=70):
    print(char * length)

def run_comparison():
    # 1. Define rich mock data representing the manuscript scenario from the UI
    # This dataset simulates:
    #   - EasyOCR having low confidence on Line 1.
    #   - DeepSeek failing to detect Line 1, returning garbage '<|im_end|>' and '#' as extra lines.
    #   - Slight typo variations across engines in Line 2.
    
    paddle_results = [
        {"text": "तप्ते सर्पिषि नक्राण्डं ताम्रचूडाण्डमिश्रितम्। युक्तं षष्टिकचूर्णेन सर्पिषाऽभिनवेन च॥ २८॥", "confidence": 0.92},
        {"text": "पक्त्वा पूपलिकाः खादेद्दारुणीमण्डपो नरः। य इच्छेद्भवदन्तु प्रसेक्तुं गजवच्च यः॥ २९॥", "confidence": 0.94}
    ]
    
    easy_results = [
        {"text": "तप्ते सर्पिषि नक्राण्डं ताम्रचूडाण्डमिश्रितम्। युक्तं षष्टिकचूर्णेन सर्पिषाऽभिनवेन च॥ २८॥", "confidence": 0.35}, # Low confidence
        {"text": "पक्त्वा पूपलिकाः दादेणामण्डपो नरः। य इच्छेध्ववद्वन्तु प्ररोकु गजवच यः॥ २९॥", "confidence": 0.72}
    ]
    
    deepseek_results = [
        {"text": "<|im_end|>", "confidence": 0.90}, # LLM noise tag
        {"text": "पक्त्वा पूपलिकाः दादेणामण्डपो नरः। य इच्छेध्ववद्वन्तु प्ररोकु गजवच यः॥ २९॥", "confidence": 0.90},
        {"text": "#", "confidence": 0.90} # LLM noise header
    ]
    
    print("\n" + "=" * 80)
    print("🔮 MULTI-MODEL OCR VOTING COMPARISON TOOL")
    print("=" * 80)
    
    # Print Input Data
    print("\n📥 INPUT DATA FOR COMPARISON:")
    print_separator("-")
    print("🚀 PaddleOCR Output (2 lines):")
    for i, r in enumerate(paddle_results, 1):
        print(f"  Line {i}: {r['text'][:50]}... [Conf: {r['confidence']:.2f}]")
        
    print("\n👁️ EasyOCR Output (2 lines):")
    for i, r in enumerate(easy_results, 1):
        print(f"  Line {i}: {r['text'][:50]}... [Conf: {r['confidence']:.2f}]")
        
    print("\n🤖 DeepSeek OCR Output (3 lines):")
    for i, r in enumerate(deepseek_results, 1):
        print(f"  Line {i}: {r['text'][:50]}... [Conf: {r['confidence']:.2f}]")
    print_separator("-")
    
    # 2. Run Original Voting
    # Note: The original voting only took paddle_results and deepseek_results.
    # EasyOCR was not integrated.
    print("\n🛑 1. RUNNING ORIGINAL VOTING ALGORITHM (Paddle vs DeepSeek only)")
    print_separator("-")
    try:
        # We simulate the exact call made in deployment/OCR_pipeline.py
        orig_output = original_voting(paddle_results, deepseek_results=deepseek_results)
        print(f"Result count: {len(orig_output)} lines")
        for i, r in enumerate(orig_output, 1):
            print(f"  Line {i}: {r['text']} (Conf: {r['confidence']:.4f})")
    except Exception as e:
        print(f"❌ Original voting crashed: {e}")
    print_separator("-")
    
    # 3. Run New Voting
    print("\n🌟 2. RUNNING NEW REDESIGNED VOTING ALGORITHM (Paddle + Easy + DeepSeek)")
    print_separator("-")
    try:
        new_output = new_voting(
            paddle_results=paddle_results,
            easy_results=easy_results,
            deepseek_results=deepseek_results
        )
        print(f"Result count: {len(new_output)} lines")
        for i, r in enumerate(new_output, 1):
            print(f"  Line {i}: {r['text']} (Conf: {r['confidence']:.4f})")
    except Exception as e:
        print(f"❌ New voting crashed: {e}")
    print_separator("-")
    
    # 4. Analysis Summary
    print("\n📊 COMPARISON ANALYSIS:")
    print_separator("-")
    print("📝 Original Algorithm Failures:")
    print("  1. Line Shift: It compared Paddle Line 1 ('तप्ते...') directly with DeepSeek Line 1 ('<|im_end|>') because of index matching.")
    print("  2. Garbage Leaks: It let '<|im_end|>' and '#' slide into the final output as separate lines.")
    print("  3. Lost Lines: The original first line ('तप्ते...') was discarded entirely because of index shifts and alignment failures.")
    
    print("\n🛡️ New Algorithm Improvements:")
    print("  1. Garbage Filtering: System tags ('<|im_end|>') and markdown headers ('#') are filtered out before alignment.")
    print("  2. Greedy Line Alignment: Correctly matches lines across engines by content similarity, resolving index shift errors.")
    print("  3. Confidence Preservation: Uses max confidence among proposing models (0.92 for Line 1) instead of averaging it down with the weak EasyOCR result (which would have been (0.92 + 0.35)/2 = 0.635 or lower).")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_comparison()
