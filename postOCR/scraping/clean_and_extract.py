import re
from pathlib import Path

def extract_devanagari_words(text: str):
    """
    Keeps ONLY Devanagari Unicode characters (U+0900–U+097F) and spaces.
    Removes everything else (punctuation, numbers, Latin letters, etc).
    Returns list of unique words.
    """
    # Remove non-Devanagari characters, keep only Devanagari and spaces
    cleaned = re.sub(r"[^\u0900-\u097F\s]", " ", text)
    
    # Split into words and remove empty strings
    words = [w.strip() for w in cleaned.split() if w.strip()]
    
    return words

def process_scraped_file(input_file="postocr/data/scraped_sanskrit.txt", 
                        output_file="postocr/data/scraped_samhita.txt"):
    """
    Read scraped Sanskrit text, extract pure Devanagari words, 
    keep only unique words, and save to new file.
    """
    
    print(f"📖 Reading: {input_file}")
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Read {len(content)} characters")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # Extract all words
    print("\n🔍 Extracting Devanagari words...")
    all_words = extract_devanagari_words(content)
    print(f"✅ Extracted {len(all_words)} total words")
    
    # Get unique words (preserve order)
    print("\n🔄 Removing duplicates...")
    unique_words = list(dict.fromkeys(all_words))  # Preserves order
    print(f"✅ Found {len(unique_words)} unique words")
    
    # Statistics
    duplicate_count = len(all_words) - len(unique_words)
    print(f"📊 Duplicates removed: {duplicate_count}")
    
    # Save to file
    print(f"\n💾 Saving to: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(unique_words))
        print(f"✅ Saved {len(unique_words)} unique words")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return
    
    # Show samples
    print(f"\n📋 First 20 unique words:")
    for i, word in enumerate(unique_words[:20], 1):
        print(f"  {i}. {word}")
    
    print(f"\n📋 Last 20 unique words:")
    for i, word in enumerate(unique_words[-20:], len(unique_words)-19):
        print(f"  {i}. {word}")
    
    print(f"\n{'='*50}")
    print(f"✨ Successfully cleaned and extracted!")
    print(f"{'='*50}")

if __name__ == "__main__":
    # Check if input file exists
    input_file = "postocr/data/scraped_sanskrit.txt"
    output_file = "postocr/data/scraped_samhita.txt"
    
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
    else:
        process_scraped_file(input_file, output_file)
