import json
from pathlib import Path

# Define paths
root_dir = Path(__file__).parent.parent.parent
data_dir = root_dir / "data" / "processed"
vocab_path = root_dir / "data" / "vocab.json"

# Data files to scan
data_files = [
    data_dir / "train.json",
    data_dir / "validation.json",
    data_dir / "test.json",
    data_dir / "ood_test.json"
]

print("=" * 60)
print("Building Vocabulary from All Datasets")
print("=" * 60)

# Collect all unique characters from all datasets
chars = set()
total_samples = 0

for data_file in data_files:
    if data_file.exists():
        print(f"\n📖 Processing: {data_file.name}")
        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"   Samples: {len(data)}")
        total_samples += len(data)
        
        for row in data:
            # Collect chars from both source and target
            if "ocr_text" in row:
                chars |= set(row["ocr_text"])
            if "corrected_text" in row:
                chars |= set(row["corrected_text"])
            # Also handle target_text if it exists
            if "target_text" in row:
                chars |= set(row["target_text"])
    else:
        print(f"\n⚠️  Skipping: {data_file.name} (not found)")

# Build vocabulary with special tokens
print(f"\n🔤 Building vocabulary...")
vocab = ["<PAD>", "<SOS>", "<EOS>", "<UNK>"] + sorted(chars)
char2idx = {c: i for i, c in enumerate(vocab)}
idx2char = {str(i): c for c, i in char2idx.items()}  # Keys as strings for JSON

# Save vocabulary
vocab_data = {
    "vocab": vocab,
    "char2idx": char2idx,
    "idx2char": idx2char,
    "vocab_size": len(vocab)
}

print(f"\n💾 Saving vocabulary to: {vocab_path}")
with open(vocab_path, "w", encoding="utf-8") as f:
    json.dump(vocab_data, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("✅ Vocabulary built successfully!")
print("=" * 60)
print(f"📊 Total samples processed: {total_samples}")
print(f"📝 Unique characters: {len(chars)}")
print(f"📚 Vocabulary size: {len(vocab)} (including special tokens)")
print(f"🔖 Special tokens: <PAD>, <SOS>, <EOS>, <UNK>")
print(f"💾 Saved to: {vocab_path}")
print("=" * 60)
