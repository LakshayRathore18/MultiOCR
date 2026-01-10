"""
Evaluate OCR Correction Model - See Predictions vs Ground Truth
"""
import json
import torch
from infer import OCRCorrector
from cer import compute_cer as calculate_cer
from colorama import init, Fore, Style
import sys

init(autoreset=True)


def evaluate_model(checkpoint_path, data_path="train.json", num_samples=10):
    """
    Evaluate model and show predictions
    
    Args:
        checkpoint_path: Path to trained model checkpoint
        data_path: Path to test data
        num_samples: Number of samples to display
    """
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}OCR Correction Model Evaluation")
    print("=" * 80)
    
    # Load model
    print(f"\n{Fore.YELLOW}Loading model...{Style.RESET_ALL}")
    corrector = OCRCorrector(checkpoint_path)
    
    # Load test data
    print(f"{Fore.YELLOW}Loading test data...{Style.RESET_ALL}")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"\nTotal samples: {len(data)}")
    print(f"Evaluating on: {min(num_samples, len(data))} samples\n")
    
    # Evaluate
    total_cer = 0
    total_length = 0
    
    for i, item in enumerate(data[:num_samples]):
        ocr_text = item["ocr_text"]
        ground_truth = item["corrected_text"]
        
        # Get model prediction
        prediction = corrector.correct(ocr_text)
        
        # Calculate CER
        cer = calculate_cer(ground_truth, prediction)
        original_cer = calculate_cer(ground_truth, ocr_text)
        
        total_cer += cer * len(ground_truth)
        total_length += len(ground_truth)
        
        # Display result
        print(f"{Fore.CYAN}{'=' * 80}")
        print(f"Sample {i + 1}/{min(num_samples, len(data))}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}OCR Input (Original):{Style.RESET_ALL}")
        print(f"{ocr_text[:200]}{'...' if len(ocr_text) > 200 else ''}")
        
        print(f"\n{Fore.GREEN}Model Prediction:{Style.RESET_ALL}")
        print(f"{prediction[:200]}{'...' if len(prediction) > 200 else ''}")
        
        print(f"\n{Fore.BLUE}Ground Truth:{Style.RESET_ALL}")
        print(f"{ground_truth[:200]}{'...' if len(ground_truth) > 200 else ''}")
        
        print(f"\n{Fore.MAGENTA}Metrics:{Style.RESET_ALL}")
        print(f"  Original CER: {original_cer:.2%} (OCR vs Ground Truth)")
        print(f"  Model CER:    {cer:.2%} (Prediction vs Ground Truth)")
        
        if cer < original_cer:
            improvement = ((original_cer - cer) / original_cer) * 100
            print(f"  {Fore.GREEN}✓ Improvement: {improvement:.1f}%{Style.RESET_ALL}")
        elif cer > original_cer:
            degradation = ((cer - original_cer) / original_cer) * 100
            print(f"  {Fore.RED}✗ Degradation: {degradation:.1f}%{Style.RESET_ALL}")
        else:
            print(f"  {Fore.YELLOW}= No change{Style.RESET_ALL}")
        
        print()
    
    # Summary
    avg_cer = total_cer / total_length if total_length > 0 else 0
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"Summary")
    print(f"{'=' * 80}{Style.RESET_ALL}")
    print(f"Average CER: {avg_cer:.2%}")
    print(f"Samples evaluated: {min(num_samples, len(data))}")
    print(f"Total characters: {total_length:,}")
    
    # Accuracy categories
    if avg_cer < 0.05:
        print(f"\n{Fore.GREEN}✓ Excellent: CER < 5%{Style.RESET_ALL}")
    elif avg_cer < 0.10:
        print(f"\n{Fore.GREEN}✓ Good: CER < 10%{Style.RESET_ALL}")
    elif avg_cer < 0.20:
        print(f"\n{Fore.YELLOW}⚠ Acceptable: CER < 20%{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}✗ Needs improvement: CER > 20%{Style.RESET_ALL}")
    
    print()


def compare_single(checkpoint_path, ocr_text, ground_truth=None):
    """Compare single prediction"""
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}Single Prediction Comparison")
    print("=" * 80)
    
    corrector = OCRCorrector(checkpoint_path)
    prediction = corrector.correct(ocr_text)
    
    print(f"\n{Fore.YELLOW}Input (OCR):{Style.RESET_ALL}")
    print(ocr_text)
    
    print(f"\n{Fore.GREEN}Prediction:{Style.RESET_ALL}")
    print(prediction)
    
    if ground_truth:
        print(f"\n{Fore.BLUE}Ground Truth:{Style.RESET_ALL}")
        print(ground_truth)
        
        cer = calculate_cer(ground_truth, prediction)
        original_cer = calculate_cer(ground_truth, ocr_text)
        
        print(f"\n{Fore.MAGENTA}Metrics:{Style.RESET_ALL}")
        print(f"  Original CER: {original_cer:.2%}")
        print(f"  Model CER:    {cer:.2%}")
        
        if cer < original_cer:
            improvement = ((original_cer - cer) / original_cer) * 100
            print(f"  {Fore.GREEN}✓ Improvement: {improvement:.1f}%{Style.RESET_ALL}")
    
    print()


def main():
    """Main evaluation function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python evaluate.py <checkpoint_path> [num_samples]")
        print("\nExample:")
        print("  python evaluate.py checkpoints/best.ckpt 10")
        print("  python evaluate.py checkpoints/ocr-correction-epoch=05-val_loss=0.1234.ckpt 20")
        return
    
    checkpoint_path = sys.argv[1]
    num_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    evaluate_model(checkpoint_path, num_samples=num_samples)


if __name__ == "__main__":
    main()
