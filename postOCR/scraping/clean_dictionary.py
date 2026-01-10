import re
from pathlib import Path

def clean_devanagari_word(word: str):
    """
    Remove non-Devanagari characters from a word.
    Keeps ONLY Devanagari Unicode characters (U+0900–U+097F).
    Returns cleaned word or empty string if nothing left.
    """
    # Remove non-Devanagari characters, keep only Devanagari
    cleaned = re.sub(r"[^\u0900-\u097F]", "", word)
    return cleaned.strip()

def clean_dictionary_file(input_file="data/sample_book/Dict.txt", 
                         output_file="data/sample_book/Dict_cleaned.txt"):
    """
    Read dictionary, clean corrupted words, remove duplicates, and save.
    """
    
    print(f"📖 Reading dictionary: {input_file}")
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"✅ Read {len(lines)} entries")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # Clean words
    print("\n🔍 Cleaning corrupted words...")
    cleaned_words = []
    removed_count = 0
    
    for i, line in enumerate(lines):
        word = line.strip()
        if not word:
            continue
        
        cleaned = clean_devanagari_word(word)
        
        # Only keep words that have content after cleaning
        if cleaned and len(cleaned) >= 2:  # Minimum 2 characters
            cleaned_words.append(cleaned)
        else:
            removed_count += 1
            if removed_count <= 10:  # Show first 10 removed words
                print(f"  ❌ Removed: '{word}' → '{cleaned}'")
    
    print(f"✅ Cleaned {len(cleaned_words)} valid words")
    print(f"🗑️ Removed {removed_count} corrupted/empty words")
    
    # Remove duplicates (preserve order)
    print("\n🔄 Removing duplicates...")
    unique_words = list(dict.fromkeys(cleaned_words))
    duplicate_count = len(cleaned_words) - len(unique_words)
    print(f"✅ Found {len(unique_words)} unique words")
    print(f"📊 Duplicates removed: {duplicate_count}")
    
    # Save cleaned dictionary
    print(f"\n💾 Saving to: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(unique_words))
        print(f"✅ Saved {len(unique_words)} cleaned words")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return
    
    # Show statistics
    print(f"\n📊 Statistics:")
    print(f"  Original entries: {len(lines)}")
    print(f"  After cleaning: {len(cleaned_words)}")
    print(f"  Unique words: {len(unique_words)}")
    print(f"  Space saved: {len(lines) - len(unique_words)} entries")
    
    # Show samples
    print(f"\n📋 First 20 words:")
    for i, word in enumerate(unique_words[:20], 1):
        print(f"  {i}. {word}")
    
    print(f"\n📋 Last 20 words:")
    for i, word in enumerate(unique_words[-20:], len(unique_words)-19):
        print(f"  {i}. {word}")
    
    print(f"\n{'='*60}")
    print(f"✨ Dictionary cleaning complete!")
    print(f"{'='*60}")
    print(f"\n💡 Next steps:")
    print(f"  1. Review the cleaned dictionary: {output_file}")
    print(f"  2. If satisfied, backup original: move Dict.txt Dict_original.txt")
    print(f"  3. Replace: move Dict_cleaned.txt Dict.txt")
    print(f"  4. Restart the app to reload dictionary")

if __name__ == "__main__":
    input_file = "data/sample_book/Dict.txt"
    output_file = "data/sample_book/Dict_cleaned.txt"
    
    if not Path(input_file).exists():
        print(f"❌ Dictionary file not found: {input_file}")
    else:
        clean_dictionary_file(input_file, output_file)
