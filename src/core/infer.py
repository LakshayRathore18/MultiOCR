"""
Inference script for OCR Correction Model
"""
import json
import torch
from model import OCRCorrectionModel


class OCRCorrector:
    """OCR text correction using trained model"""
    
    def __init__(self, checkpoint_path, vocab_path="vocab.json"):
        """
        Args:
            checkpoint_path: Path to trained model checkpoint
            vocab_path: Path to vocabulary JSON
        """
        # Load vocabulary
        with open(vocab_path, encoding="utf-8") as f:
            vocab_data = json.load(f)
            self.char2idx = vocab_data["char2idx"]
            self.idx2char = vocab_data["idx2char"]
            self.vocab_size = vocab_data["vocab_size"]
        
        # Special tokens
        self.pad_idx = self.char2idx["<PAD>"]
        self.sos_idx = self.char2idx["<SOS>"]
        self.eos_idx = self.char2idx["<EOS>"]
        self.unk_idx = self.char2idx["<UNK>"]
        
        # Load model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = OCRCorrectionModel.load_from_checkpoint(checkpoint_path)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"✅ Model loaded from {checkpoint_path}")
        print(f"   Device: {self.device}")
        print(f"   Vocab size: {self.vocab_size}")
    
    def text_to_tensor(self, text):
        """Convert text to tensor"""
        indices = [self.sos_idx]
        for c in text:
            indices.append(self.char2idx.get(c, self.unk_idx))
        indices.append(self.eos_idx)
        return torch.tensor([indices], dtype=torch.long).to(self.device)
    
    def tensor_to_text(self, tensor):
        """Convert tensor to text"""
        text = []
        for idx in tensor[0].tolist():
            if idx == self.eos_idx:
                break
            if idx not in [self.pad_idx, self.sos_idx]:
                text.append(self.idx2char[str(idx)])
        return "".join(text)
    
    @torch.no_grad()
    def correct(self, ocr_text, max_len=512):
        """
        Correct OCR text
        
        Args:
            ocr_text: Text with OCR errors
            max_len: Maximum generation length
        
        Returns:
            Corrected text
        """
        # Convert to tensor
        src = self.text_to_tensor(ocr_text)
        
        # Generate correction
        output = self.model.generate(
            src,
            max_len=max_len,
            sos_idx=self.sos_idx,
            eos_idx=self.eos_idx
        )
        
        # Convert back to text
        corrected_text = self.tensor_to_text(output)
        
        return corrected_text
    
    def correct_batch(self, ocr_texts, max_len=512):
        """Correct multiple OCR texts"""
        results = []
        for text in ocr_texts:
            corrected = self.correct(text, max_len)
            results.append(corrected)
        return results


def main():
    """Demo inference"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python infer.py <checkpoint_path> [text]")
        print("\nExample:")
        print('  python infer.py checkpoints/best.ckpt "श्रीभगवानुवाच"')
        print("\nOr run interactive mode:")
        print("  python infer.py checkpoints/best.ckpt")
        return
    
    checkpoint_path = sys.argv[1]
    
    # Initialize corrector
    corrector = OCRCorrector(checkpoint_path)
    
    if len(sys.argv) > 2:
        # Single correction
        ocr_text = sys.argv[2]
        print(f"\nInput:  {ocr_text}")
        corrected = corrector.correct(ocr_text)
        print(f"Output: {corrected}")
    else:
        # Interactive mode
        print("\n" + "=" * 60)
        print("Interactive OCR Correction")
        print("=" * 60)
        print("Enter OCR text to correct (or 'quit' to exit)\n")
        
        while True:
            ocr_text = input("OCR Text: ").strip()
            if ocr_text.lower() in ['quit', 'exit', 'q']:
                break
            if not ocr_text:
                continue
            
            corrected = corrector.correct(ocr_text)
            print(f"Corrected: {corrected}\n")


if __name__ == "__main__":
    main()

