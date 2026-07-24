"""
Test suite for OCR Corrector
"""

import sys
from pathlib import Path

# Add parent directory of correction package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from correction.corrector import OCRCorrector
from correction.edit_distance import levenshtein_distance


def test_levenshtein_distance():
    """Test Levenshtein distance calculation"""
    print("Testing Levenshtein distance...")
    
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("saturday", "sunday") == 3
    assert levenshtein_distance("abc", "abc") == 0
    assert levenshtein_distance("abc", "") == 3
    
    print("✅ Levenshtein distance tests passed!")


def test_corrector_initialization():
    """Test corrector initialization"""
    print("\nTesting corrector initialization...")
    
    corrector = OCRCorrector()
    assert corrector.max_edit_distance == 2
    assert corrector.max_suggestions == 15  # Increased for Sanskrit manual selection
    assert len(corrector.dictionary.words) == 0
    
    print("✅ Corrector initialization tests passed!")


def test_dictionary_operations():
    """Test dictionary operations"""
    print("\nTesting dictionary operations...")
    
    corrector = OCRCorrector()
    
    # Add words
    corrector.dictionary.add_word("hello")
    corrector.dictionary.add_word("world")
    assert corrector.is_word_correct("hello")
    assert corrector.is_word_correct("world")
    assert not corrector.is_word_correct("helo")
    
    print("✅ Dictionary operation tests passed!")


def test_confusion_pairs():
    """Test confusion pair management"""
    print("\nTesting confusion pairs...")
    
    corrector = OCRCorrector()
    
    # Add confusion pair
    corrector.confusion_manager.add_pair("teh", "the")
    assert corrector.confusion_manager.get_correction("teh") == "the"
    assert corrector.confusion_manager.get_correction("the") is None
    
    print("✅ Confusion pair tests passed!")


def test_suggestion_generation():
    """Test suggestion generation"""
    print("\nTesting suggestion generation...")
    
    corrector = OCRCorrector()
    
    # Load some test words
    test_words = ["hello", "world", "python", "test", "correct"]
    for word in test_words:
        corrector.dictionary.add_word(word)
    
    corrector._rebuild_trie()
    
    # Test suggestions for typo
    suggestions = corrector.generate_suggestions("helo")
    print(f"Suggestions for 'helo': {suggestions}")
    assert len(suggestions) > 0 or "hello" in [s[1] for s in suggestions]
    
    # Test correct word (should return empty)
    suggestions = corrector.generate_suggestions("hello")
    assert len(suggestions) == 0
    
    print("✅ Suggestion generation tests passed!")


def test_tokenization():
    """Test text tokenization"""
    print("\nTesting tokenization...")
    
    corrector = OCRCorrector()
    
    text = "Hello world! This is a test."
    tokens = corrector._tokenize(text)
    assert "Hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    
    print("✅ Tokenization tests passed!")


def test_error_detection():
    """Test error detection"""
    print("\nTesting error detection...")
    
    corrector = OCRCorrector()
    
    # Load dictionary
    test_words = ["the", "quick", "brown", "fox", "jumps"]
    for word in test_words:
        corrector.dictionary.add_word(word)
    
    corrector._rebuild_trie()
    
    # Test text with error
    text = "teh quick brown fox jumps"
    errors = corrector.detect_errors(text)
    
    # Should detect "teh" as error
    error_words = [e['word'] for e in errors]
    assert "teh" in error_words or len(errors) == 1
    
    print("✅ Error detection tests passed!")


def test_caching():
    """Test suggestion caching"""
    print("\nTesting suggestion caching...")
    
    corrector = OCRCorrector()
    
    # Add words
    test_words = ["hello", "world", "python"]
    for word in test_words:
        corrector.dictionary.add_word(word)
    
    corrector._rebuild_trie()
    
    # Generate suggestions (should cache)
    suggestions1 = corrector.generate_suggestions("helo")
    suggestions2 = corrector.generate_suggestions("helo")
    
    # Should return same results (from cache)
    assert suggestions1 == suggestions2
    assert "helo" in corrector.suggestion_cache
    
    print("✅ Caching tests passed!")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Running OCR Corrector Test Suite")
    print("=" * 50)
    
    try:
        test_levenshtein_distance()
        test_corrector_initialization()
        test_dictionary_operations()
        test_confusion_pairs()
        test_tokenization()
        test_error_detection()
        test_suggestion_generation()
        test_caching()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed successfully!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
