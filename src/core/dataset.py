"""
OCR Correction Dataset for PyTorch
"""
import json
import torch
from torch.utils.data import Dataset
from torch.nn.utils.rnn import pad_sequence


class OCRCorrectionDataset(Dataset):
    """Dataset for OCR text correction"""
    
    def __init__(self, data_path="train.json", vocab_path="vocab.json", max_len=512):
        """
        Args:
            data_path: Path to training data JSON
            vocab_path: Path to vocabulary JSON
            max_len: Maximum sequence length
        """
        # Load data
        with open(data_path, encoding="utf-8") as f:
            self.data = json.load(f)
        
        # Load vocabulary
        with open(vocab_path, encoding="utf-8") as f:
            vocab_data = json.load(f)
            self.char2idx = vocab_data["char2idx"]
            self.idx2char = vocab_data["idx2char"]
            self.vocab_size = vocab_data["vocab_size"]
        
        # Special token indices
        self.pad_idx = self.char2idx["<PAD>"]
        self.sos_idx = self.char2idx["<SOS>"]
        self.eos_idx = self.char2idx["<EOS>"]
        self.unk_idx = self.char2idx["<UNK>"]
        
        self.max_len = max_len
        
        print(f"Loaded {len(self.data)} samples")
        print(f"Vocabulary size: {self.vocab_size}")
    
    def __len__(self):
        return len(self.data)
    
    def text_to_indices(self, text):
        """Convert text to list of indices"""
        return [self.char2idx.get(c, self.unk_idx) for c in text]
    
    def __getitem__(self, idx):
        """Get a single sample"""
        item = self.data[idx]
        
        # Support both formats: (ocr_text, corrected_text) and (input_text, target_text)
        input_text = item.get("input_text", item.get("ocr_text", ""))[:self.max_len]
        target_text = item.get("target_text", item.get("corrected_text", ""))[:self.max_len]
        
        # Encode input
        input_indices = [self.sos_idx] + self.text_to_indices(input_text) + [self.eos_idx]
        
        # Encode target
        target_indices = [self.sos_idx] + self.text_to_indices(target_text) + [self.eos_idx]
        
        return {
            "input": torch.tensor(input_indices, dtype=torch.long),
            "target": torch.tensor(target_indices, dtype=torch.long),
            "input_text": input_text,
            "target_text": target_text
        }


def collate_fn(batch):
    """Custom collate function for batching with padding"""
    inputs = [item["input"] for item in batch]
    targets = [item["target"] for item in batch]
    
    # Pad sequences
    inputs_padded = pad_sequence(inputs, batch_first=True, padding_value=0)
    targets_padded = pad_sequence(targets, batch_first=True, padding_value=0)
    
    return {
        "input": inputs_padded,
        "target": targets_padded,
        "input_texts": [item["input_text"] for item in batch],
        "target_texts": [item["target_text"] for item in batch]
    }
