"""
Devanagari Unicode Validator and Corrector
Handles proper matra (vowel sign) placement and character validation
"""

# Unicode ranges for Devanagari (U+0900 to U+097F)
INDEPENDENT_VOWELS = set(range(0x0905, 0x0915))  # अ to औ
CONSONANTS = set(range(0x0915, 0x093A))  # क to ह
VOWEL_SIGNS = set(range(0x093E, 0x094D)) - {0x094D}  # ◌ा to ◌ौ (matras)
VIRAMA = 0x094D  # ◌्  (halant)
DIACRITICS = {0x0901, 0x0902, 0x0903}  # ◌ँ, ◌ं, ◌ः
DANDA = {0x0964, 0x0965}  # । ॥
DIGITS = set(range(0x0966, 0x0970))  # ० to ९
NUKTA = 0x093C  # ◌़
AVAGRAHA = 0x093D  # ऽ

# Additional consonants
ADDITIONAL_CONSONANTS = {0x0931, 0x0934, 0x0958, 0x0959, 0x095A, 0x095B, 0x095C, 0x095D, 0x095E, 0x095F}

# Combining characters (matras that combine with consonants)
COMBINING_SIGNS = VOWEL_SIGNS | {VIRAMA, NUKTA} | DIACRITICS

def is_consonant(ch):
    """Check if character is a Devanagari consonant"""
    code = ord(ch) if isinstance(ch, str) else ch
    return code in CONSONANTS or code in ADDITIONAL_CONSONANTS

def is_vowel_sign(ch):
    """Check if character is a matra (vowel sign)"""
    code = ord(ch) if isinstance(ch, str) else ch
    return code in VOWEL_SIGNS

def is_independent_vowel(ch):
    """Check if character is an independent vowel"""
    code = ord(ch) if isinstance(ch, str) else ch
    return code in INDEPENDENT_VOWELS

def is_virama(ch):
    """Check if character is virama/halant"""
    code = ord(ch) if isinstance(ch, str) else ch
    return code == VIRAMA

def is_diacritic(ch):
    """Check if character is a diacritic mark"""
    code = ord(ch) if isinstance(ch, str) else ch
    return code in DIACRITICS

def is_devanagari(ch):
    """Check if character belongs to Devanagari script"""
    code = ord(ch) if isinstance(ch, str) else ch
    return 0x0900 <= code <= 0x097F

def validate_devanagari_sequence(text):
    """
    Validate Devanagari text for linguistically invalid sequences.
    Flags issues where matras are missing or misplaced.
    
    Returns:
        list of tuples: (index, issue_description, character)
    """
    issues = []
    prev = None
    prev_idx = -1
    
    for i, ch in enumerate(text):
        if not is_devanagari(ch):
            prev = ch
            prev_idx = i
            continue
            
        code = ord(ch)
        
        # Rule 1: Matra must follow a consonant or another matra
        if is_vowel_sign(ch):
            if prev is None or (not is_consonant(prev) and not is_vowel_sign(prev) and not is_virama(prev)):
                issues.append((i, "Matra without base consonant", ch))
        
        # Rule 2: Virama must follow a consonant
        if is_virama(ch):
            if prev is None or not is_consonant(prev):
                issues.append((i, "Virama without consonant", ch))
        
        # Rule 3: Multiple matras without consonant base
        if is_vowel_sign(ch) and is_vowel_sign(prev):
            # Check if there's a consonant before the previous matra
            if prev_idx > 0:
                before_prev = text[prev_idx - 1]
                if not is_consonant(before_prev):
                    issues.append((i, "Multiple matras without consonant", ch))
        
        # Rule 4: Diacritic marks should come after consonant or matra
        if is_diacritic(ch):
            if prev is None or (not is_consonant(prev) and not is_vowel_sign(prev)):
                issues.append((i, "Diacritic without proper base", ch))
        
        prev = ch
        prev_idx = i
    
    return issues

def correct_matra_placement(text):
    """
    Attempt to correct common matra placement errors.
    
    Strategy:
    1. If matra appears without consonant, try to find nearby consonant
    2. Reorder sequences to be linguistically valid
    3. Remove orphaned matras if no consonant found
    
    Returns:
        str: Corrected text
    """
    if not text:
        return text
    
    result = []
    i = 0
    
    while i < len(text):
        ch = text[i]
        
        # If it's not Devanagari, keep as is
        if not is_devanagari(ch):
            result.append(ch)
            i += 1
            continue
        
        # If it's a matra at the start or after non-consonant
        if is_vowel_sign(ch):
            # Check if previous character is valid base
            if len(result) > 0 and is_consonant(result[-1]):
                result.append(ch)
            else:
                # Look ahead for a consonant within next 2 characters
                found_consonant = False
                for j in range(i + 1, min(i + 3, len(text))):
                    if is_consonant(text[j]):
                        # Move matra after the consonant
                        result.append(text[j])
                        result.append(ch)
                        i = j
                        found_consonant = True
                        break
                
                if not found_consonant:
                    # Skip orphaned matra
                    pass
            i += 1
            continue
        
        # If it's a virama without consonant before it
        if is_virama(ch):
            if len(result) > 0 and is_consonant(result[-1]):
                result.append(ch)
            else:
                # Skip invalid virama
                pass
            i += 1
            continue
        
        # Normal character
        result.append(ch)
        i += 1
    
    return ''.join(result)

def analyze_text_quality(text):
    """
    Analyze the quality of Devanagari text.
    
    Returns:
        dict: Statistics about the text quality
    """
    if not text:
        return {
            'total_chars': 0,
            'devanagari_chars': 0,
            'consonants': 0,
            'vowels': 0,
            'matras': 0,
            'issues': [],
            'quality_score': 0.0
        }
    
    total_chars = len(text)
    devanagari_chars = sum(1 for ch in text if is_devanagari(ch))
    consonants = sum(1 for ch in text if is_consonant(ch))
    vowels = sum(1 for ch in text if is_independent_vowel(ch))
    matras = sum(1 for ch in text if is_vowel_sign(ch))
    
    issues = validate_devanagari_sequence(text)
    
    # Calculate quality score (0-1)
    if devanagari_chars > 0:
        error_rate = len(issues) / devanagari_chars
        quality_score = max(0.0, 1.0 - error_rate)
    else:
        quality_score = 1.0
    
    return {
        'total_chars': total_chars,
        'devanagari_chars': devanagari_chars,
        'consonants': consonants,
        'vowels': vowels,
        'matras': matras,
        'issues': issues,
        'quality_score': quality_score
    }

def clean_devanagari_text(text):
    """
    Clean and correct Devanagari text from OCR output.
    
    Process:
    1. Validate sequences
    2. Correct matra placement
    3. Remove invalid characters
    
    Returns:
        str: Cleaned text
    """
    if not text:
        return text
    
    # First pass: correct matra placement
    corrected = correct_matra_placement(text)
    
    # Second pass: remove remaining invalid sequences
    result = []
    for ch in corrected:
        if not is_devanagari(ch):
            result.append(ch)
            continue
        
        # Keep valid characters
        if (is_consonant(ch) or is_independent_vowel(ch) or 
            is_vowel_sign(ch) or is_virama(ch) or 
            is_diacritic(ch) or ord(ch) in DANDA or 
            ord(ch) in DIGITS or ord(ch) == NUKTA or 
            ord(ch) == AVAGRAHA):
            result.append(ch)
    
    return ''.join(result)
