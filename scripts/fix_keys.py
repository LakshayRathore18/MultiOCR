import json
import os

# Get the parent directory (multiocr root)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

# Input and output paths
input_file = os.path.join(parent_dir, "train.json")
output_file = os.path.join(parent_dir, "train_fixed.json")

with open(input_file, encoding="utf-8") as f:
    data = json.load(f)

fixed = []
for row in data:
    fixed.append({
        "input_text": row["ocr_text"],
        "target_text": row["corrected_text"]
    })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(fixed, f, ensure_ascii=False, indent=2)

print(f"✅ Keys fixed: {len(fixed)} entries")
print(f"   Input:  {input_file}")
print(f"   Output: {output_file}")
