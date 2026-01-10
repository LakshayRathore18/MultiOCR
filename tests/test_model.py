"""
Quick Test Script - Test model on sample data before full evaluation
"""
import json
from infer import OCRCorrector
from colorama import init, Fore, Style

init(autoreset=True)


def quick_test(checkpoint_path):
    """Quick test on first 3 samples"""
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print("Quick Model Test - First 3 Samples")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")
    
    # Load model
    print(f"{Fore.YELLOW}Loading model...{Style.RESET_ALL}")
    corrector = OCRCorrector(checkpoint_path)
    
    # Load data
    with open("train.json", encoding="utf-8") as f:
        data = json.load(f)
    
    # Test on first 3 samples
    for i, item in enumerate(data[:3], 1):
        ocr_text = item["ocr_text"]
        ground_truth = item["corrected_text"]
        
        print(f"\n{Fore.CYAN}Test {i}/3:")
        print(f"{'-' * 80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}OCR Input:{Style.RESET_ALL}")
        print(f"{ocr_text[:150]}...")
        
        print(f"\n{Fore.GREEN}Model Output:{Style.RESET_ALL}")
        prediction = corrector.correct(ocr_text)
        print(f"{prediction[:150]}...")
        
        print(f"\n{Fore.BLUE}Expected:{Style.RESET_ALL}")
        print(f"{ground_truth[:150]}...")
        
        # Quick visual check
        if prediction.strip() == ground_truth.strip():
            print(f"\n{Fore.GREEN}✓ Perfect Match!{Style.RESET_ALL}")
        elif prediction[:50] == ground_truth[:50]:
            print(f"\n{Fore.YELLOW}~ Partial Match (beginning matches){Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}⚠ Different output{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print("Test completed! Run evaluate.py for detailed metrics.")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage: python test_model.py <checkpoint_path>")
        print("\nExample:")
        print("  python test_model.py checkpoints/ocr-correction-epoch=10-val_loss=0.1234.ckpt")
        print("\nAvailable checkpoints:")
        import os
        if os.path.exists("checkpoints"):
            for f in os.listdir("checkpoints"):
                if f.endswith(".ckpt"):
                    print(f"  - checkpoints/{f}")
    else:
        quick_test(sys.argv[1])
