"""
PostOCR Correction Integration for Flask
Initializes and manages OCR correction engine
"""

import os
import sys
from pathlib import Path

# Add correction to path
correction_path = os.path.join(os.path.dirname(__file__), 'correction')
sys.path.insert(0, correction_path)

from correction.src.core.corrector import OCRCorrector

# Global corrector instance
_corrector = None

def get_corrector():
    """Get or initialize the corrector"""
    global _corrector
    if _corrector is None:
        _corrector = OCRCorrector()
        _initialize_corrector()
    return _corrector

def _initialize_corrector():
    """Initialize corrector with data files and build trie"""
    corrector = _corrector
    base_dir = Path(__file__).parent / "correction"
    
    print("\n" + "="*60)
    print("📖 PostOCR Correction Module Initialization")
    print("="*60)
    
    try:
        # Load dictionary
        sample_dict_path = base_dir / "data" / "sample_book" / "Dict.txt"
        if sample_dict_path.exists():
            corrector.load_dictionary(str(sample_dict_path))
            print(f"  ✅ Dictionary loaded (base vocabulary)")
        else:
            print(f"  ⚠️  Dictionary not found: {sample_dict_path}")
        
        # Load confusion pairs
        learned_confusions_path = base_dir / "data" / "learned_confusions.txt"
        if learned_confusions_path.exists():
            corrector.load_confusion_pairs(str(learned_confusions_path))
            print(f"  ✅ Confusion pairs loaded (learned OCR patterns)")
        
        # Load domain words
        learned_domain_path = base_dir / "data" / "learned_domain_words.txt"
        if learned_domain_path.exists():
            corrector.dictionary.load_domain_words(str(learned_domain_path))
            print(f"  ✅ Domain words loaded (Sanskrit-specific terms)")
        
        # Load samhita words
        samhita_path = base_dir / "data" / "scraped_samhita.txt"
        if samhita_path.exists():
            try:
                with open(samhita_path, 'r', encoding='utf-8') as f:
                    samhita_words = [line.strip() for line in f.readlines() 
                                   if line.strip() and len(line.strip()) >= 5]
                    corrector.dictionary.add_domain_words(samhita_words)
                    print(f"  ✅ Samhita words loaded ({len(samhita_words)} words)")
            except Exception as e:
                print(f"  ⚠️  Error auto-loading samhita: {e}")
        
        # Load CCRAS wordlist
        ccras_path = base_dir / "data" / "ccras_wordlist.txt"
        if ccras_path.exists():
            try:
                with open(ccras_path, 'r', encoding='utf-8') as f:
                    ccras_words = [line.strip() for line in f.readlines() 
                                   if line.strip() and len(line.strip()) >= 2]
                    corrector.dictionary.add_domain_words(ccras_words)
                    print(f"  ✅ CCRAS wordlist loaded ({len(ccras_words)} words)")
            except Exception as e:
                print(f"  ⚠️  Error auto-loading CCRAS wordlist: {e}")
        
        # Rebuild trie with all words
        print("\n  🔨 Building search trie with all loaded words...")
        corrector.rebuild_trie_with_domain_words()
        print("  ✅ Search trie built successfully!")
        print("\n" + "="*60)
        print("✅ PostOCR correction module ready for use!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"  ❌ Error initializing PostOCR corrector: {e}")
        print("="*60 + "\n")

def correct_text(text, confidence_threshold='MEDIUM'):
    """
    Correct OCR text using learned confusion pairs and dictionary
    
    Args:
        text: OCR text to correct
        confidence_threshold: 'HIGH', 'MEDIUM', or 'LOW'
    
    Returns:
        dict with corrected_text, errors_found, corrections_made
    """
    corrector = get_corrector()
    
    try:
        # Detect errors
        errors = corrector.detect_errors(text)
        
        # Auto-correct
        corrected = corrector.auto_correct(text, confidence_threshold)
        
        return {
            'success': True,
            'corrected_text': corrected,
            'errors_found': len(errors),
            'errors': errors,
            'confidence_threshold': confidence_threshold
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'corrected_text': text
        }

def detect_errors(text):
    """Detect OCR errors in text"""
    corrector = get_corrector()
    try:
        errors = corrector.detect_errors(text)
        return {
            'success': True,
            'errors': errors,
            'error_count': len(errors)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'errors': []
        }
def add_confusion_pair(incorrect, correct):
    """Add a new confusion pair to the corrector"""
    corrector = get_corrector()
    try:
        # Add to dictionary as domain word
        corrector.dictionary.add_domain_words([correct])
        
        # Add confusion pair so it's learned for future corrections
        corrector.confusion_manager.add_pair(incorrect, correct)
        
        # Add word to trie incrementally (much faster than rebuilding)
        corrector.trie.insert_word(correct)
        
        # Clear suggestion cache to use new word
        corrector.suggestion_cache.clear()
        
        # Persist the changes to disk
        base_dir = Path(__file__).parent / "correction"
        
        # Save updated domain words
        learned_domain_path = base_dir / "data" / "learned_domain_words.txt"
        corrector.dictionary.save_domain_words(str(learned_domain_path))
        
        # Save updated confusion pairs
        learned_confusions_path = base_dir / "data" / "learned_confusions.txt"
        corrector.confusion_manager.save_to_file(str(learned_confusions_path))
        
        print(f"✅ Added confusion pair: '{incorrect}' -> '{correct}' (persisted to disk)")
        return True
    except Exception as e:
        print(f"❌ Error adding confusion pair: {e}")
        return False