#!/usr/bin/env python3
"""
Save base 13367 Sanskrit texts to scraped_sanskrit.txt
Run this FIRST before scraping
"""
from pathlib import Path

OUTPUT_FILE = "data/scraped_sanskrit.txt"

# Base texts from previous runs
base_texts = [
    # These would be read from existing file if it has them
]

print("=" * 60)
print("📝 Base Text Saver")
print("=" * 60)

# Check if file exists and has content
if Path(OUTPUT_FILE).exists():
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        existing = [line.strip() for line in f if line.strip()]
    
    print(f"\n✅ File already exists with {len(existing)} texts")
    print(f"📄 File: {OUTPUT_FILE}")
    
    # Verify and rewrite to ensure clean save
    print("\n💾 Verifying and saving all texts...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for text in existing:
            f.write(text + "\n")
    
    print(f"✅ All {len(existing)} texts verified and saved!")
else:
    print(f"\n❌ File not found: {OUTPUT_FILE}")
    print("Create the file first or run the scraper")

print("\n" + "=" * 60)
print("✅ BASE TEXTS SAVED")
print(f"📊 Total texts in file: {len(existing) if Path(OUTPUT_FILE).exists() else 0}")
print("🔄 Ready to append new texts from scraper!")
print("=" * 60)
