"""
Debug script to see what the model is actually generating
"""
import json
import torch
from model import OCRCorrectionModel

# Load vocab
with open("vocab.json", encoding="utf-8") as f:
    vocab_data = json.load(f)
    char2idx = vocab_data["char2idx"]
    idx2char = vocab_data["idx2char"]

# Load model
checkpoint_path = "checkpoints/ocr-correction-epoch=13-val_loss=3.5673.ckpt"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = OCRCorrectionModel.load_from_checkpoint(checkpoint_path)
model.to(device)
model.eval()

print("Model loaded successfully")
print(f"Device: {device}")
print(f"Vocab size: {len(char2idx)}")

# Special tokens
pad_idx = char2idx["<PAD>"]
sos_idx = char2idx["<SOS>"]
eos_idx = char2idx["<EOS>"]
unk_idx = char2idx["<UNK>"]

print(f"\nSpecial tokens: PAD={pad_idx}, SOS={sos_idx}, EOS={eos_idx}, UNK={unk_idx}")

# Test text
test_text = "श्रीभगवानुवाच"
print(f"\nTest input: {test_text}")

# Encode
indices = [sos_idx] + [char2idx.get(c, unk_idx) for c in test_text] + [eos_idx]
src = torch.tensor([indices], dtype=torch.long).to(device)
print(f"Input tensor shape: {src.shape}")
print(f"Input indices: {src[0].tolist()[:20]}...")

# Generate
print("\n" + "="*60)
print("Generating with model...")
print("="*60)

with torch.no_grad():
    output = model.generate(
        src,
        max_len=100,
        sos_idx=sos_idx,
        eos_idx=eos_idx
    )

print(f"\nOutput tensor shape: {output.shape}")
print(f"Output indices: {output[0].tolist()}")

# Decode
decoded_chars = []
for idx in output[0].tolist():
    char = idx2char.get(str(idx), f"<UNK:{idx}>")
    decoded_chars.append(char)
    if char == "<EOS>":
        break

print(f"\nDecoded characters: {decoded_chars}")

# Final text
final_text = []
for char in decoded_chars:
    if char not in ["<PAD>", "<SOS>", "<EOS>"]:
        final_text.append(char)

result = "".join(final_text)
print(f"\nFinal output: '{result}'")
print(f"Output length: {len(result)}")

if not result.strip():
    print("\n⚠️  WARNING: Model is outputting empty text!")
    print("Possible issues:")
    print("  1. Model immediately generates EOS token")
    print("  2. Generation loop is not working")
    print("  3. Model hasn't learned anything yet")
