"""
Test Devanagari Unicode validator
"""
from ocr.devanagari_unicode import (
    validate_devanagari_sequence,
    correct_matra_placement,
    analyze_text_quality,
    clean_devanagari_text,
    is_consonant,
    is_vowel_sign
)

print("=" * 60)
print("DEVANAGARI UNICODE VALIDATOR TEST")
print("=" * 60)

# Test 1: Valid Sanskrit text
print("\n1. Testing VALID text:")
valid_text = "नमस्ते भारत"
print(f"Text: {valid_text}")
issues = validate_devanagari_sequence(valid_text)
print(f"Issues found: {len(issues)}")
if issues:
    for idx, issue, ch in issues:
        print(f"  - Index {idx}: {issue} ('{ch}')")
else:
    print("  ✓ No issues - text is valid!")

quality = analyze_text_quality(valid_text)
print(f"Quality Score: {quality['quality_score']:.2%}")
print(f"Stats: {quality['consonants']} consonants, {quality['matras']} matras")

# Test 2: Invalid text (matra without consonant)
print("\n2. Testing INVALID text (orphaned matra):")
invalid_text = "◌ानमस्ते"  # matra 'ा' at start
print(f"Text: {invalid_text}")
issues = validate_devanagari_sequence(invalid_text)
print(f"Issues found: {len(issues)}")
for idx, issue, ch in issues:
    print(f"  - Index {idx}: {issue} ('{ch}')")

corrected = correct_matra_placement(invalid_text)
print(f"Corrected: {corrected}")

# Test 3: Common OCR error (misplaced matra)
print("\n3. Testing OCR ERROR (misplaced matra):")
ocr_error = "िकताब"  # 'ि' before 'क' (should be after)
print(f"Original: {ocr_error}")
print(f"Issue: Matra 'ि' appears before consonant")

cleaned = clean_devanagari_text(ocr_error)
print(f"Cleaned: {cleaned}")

# Test 4: Complex text with multiple issues
print("\n4. Testing COMPLEX text:")
complex_text = "सं◌्कृत भाषा"
print(f"Text: {complex_text}")
issues = validate_devanagari_sequence(complex_text)
print(f"Issues found: {len(issues)}")
for idx, issue, ch in issues:
    print(f"  - Index {idx}: {issue} ('{ch}')")

cleaned = clean_devanagari_text(complex_text)
print(f"Cleaned: {cleaned}")

# Test 5: Character type detection
print("\n5. Testing CHARACTER TYPE detection:")
test_chars = [
    ('क', 'consonant'),
    ('ा', 'matra'),  # Just the matra, not combining
    ('अ', 'independent vowel'),
    ('्', 'virama'),
]

for char, expected in test_chars:
    if len(char) != 1:
        print(f"Skipping '{char}' - multi-character string")
        continue
    is_cons = is_consonant(char)
    is_matra = is_vowel_sign(char)
    print(f"'{char}' - Expected: {expected}, ", end="")
    if is_cons:
        print("Detected: consonant ✓")
    elif is_matra:
        print("Detected: matra ✓")
    else:
        print(f"Detected: other")

# Test 6: Real OCR output example
print("\n6. Testing REAL OCR OUTPUT:")
ocr_output = "िहंदी भाषा बहुत सुंदर है"  # May have matra issues
print(f"OCR Output: {ocr_output}")

quality = analyze_text_quality(ocr_output)
print(f"Quality Score: {quality['quality_score']:.2%}")
print(f"Total chars: {quality['total_chars']}")
print(f"Devanagari chars: {quality['devanagari_chars']}")
print(f"Issues: {len(quality['issues'])}")

cleaned = clean_devanagari_text(ocr_output)
print(f"Cleaned text: {cleaned}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
