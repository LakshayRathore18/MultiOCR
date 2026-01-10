#!/usr/bin/env python3
"""
Cleanup and deduplicate scraped_sanskrit.txt
Removes empty lines, duplicates, and whitespace issues
"""
from pathlib import Path

INPUT_FILE = "data/scraped_sanskrit.txt"
OUTPUT_FILE = "data/scraped_sanskrit.txt"
BACKUP_FILE = "data/scraped_sanskrit.txt.backup"

print("=" * 60)
print("📝 Sanskrit Text Deduplication Tool")
print("=" * 60)

# Read file
if not Path(INPUT_FILE).exists():
    print(f"❌ File not found: {INPUT_FILE}")
    exit(1)

print(f"\n📖 Reading from: {INPUT_FILE}")
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"📊 Total lines in file: {len(lines)}")

# Count empty lines
empty_count = sum(1 for line in lines if not line.strip())
print(f"⚪ Empty lines: {empty_count}")

# Deduplicate while preserving order of first occurrence
seen = set()
unique_texts = []
duplicate_count = 0

for line in lines:
    text = line.strip()
    if text:  # Skip empty lines
        if text not in seen:
            seen.add(text)
            unique_texts.append(text)
        else:
            duplicate_count += 1

print(f"🔄 Duplicates removed: {duplicate_count}")
print(f"✅ Unique texts: {len(unique_texts)}")

# Create backup
print(f"\n💾 Creating backup: {BACKUP_FILE}")
with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f_out:
        f_out.write(f_in.read())

# Write cleaned file
print(f"✍️ Writing cleaned file: {OUTPUT_FILE}")
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    for text in unique_texts:
        f.write(text + "\n")

print("\n" + "=" * 60)
print("✅ CLEANUP COMPLETE")
print(f"📄 Before: {len(lines)} lines ({len(seen) + duplicate_count} unique)")
print(f"📄 After: {len(unique_texts)} unique texts")
print(f"🗑️ Removed: {empty_count} empty + {duplicate_count} duplicates = {empty_count + duplicate_count} lines")
print(f"💾 Backup saved: {BACKUP_FILE}")
print("=" * 60)
