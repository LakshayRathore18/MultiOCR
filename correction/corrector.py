"""
Main OCR Corrector Engine
"""

import re
from . dictionary import Dictionary
from .confusion_pairs import ConfusionPairManager
from .edit_distance import TrieEditDistance
from .lcs import ConfusionExtractor


class OCRCorrector:
    def __init__(self):
        self.dictionary = Dictionary()
        self.confusion_manager = ConfusionPairManager()
        self.confusion_extractor = ConfusionExtractor()
        self.trie = TrieEditDistance()
        
        # For Devanagari/Sanskrit: allow distance of 2 for character modifications
        # (vowel marks, nuktā, anusvāra differences are significant but should still match)
        self.max_edit_distance = 2
        self.max_suggestions = 15  # Increased for Sanskrit manual selection
        self.suggestion_cache = {}  # Cache for suggestions
        
        self.stats = {
            'words_checked': 0,
            'errors_found': 0,
            'corrections_made': 0
        }
    
    def load_dictionary(self, filepath):
        """Load dictionary file"""
        success = self.dictionary.load_from_file(filepath)
        if success:
            self._rebuild_trie()
        return success
    
    def load_confusion_pairs(self, filepath):
        """Load confusion pairs"""
        self.confusion_manager.load_from_file(filepath)
    
    def rebuild_trie_with_domain_words(self):
        """Rebuild trie after domain words have been added"""
        self._rebuild_trie()
    
    def _rebuild_trie(self):
        """Rebuild trie from dictionary"""
        print("🔨 Building search trie...")
        self.trie = TrieEditDistance()
        self.suggestion_cache.clear()  # Clear cache when rebuilding
        
        all_words = (self.dictionary.words | 
                     self.dictionary.domain_words | 
                     self.dictionary.positive_words)
        
        self.trie.insert_words(all_words)
        print(f"✅ Trie built with {len(all_words)} words")
    
    def is_word_correct(self, word):
        """Check if word is correct"""
        if not word or len(word) < 2:
            return True
        word_lower = word.lower().strip()
        if word_lower.isdigit():
            return True
        return self.dictionary.contains(word_lower)
    
    def generate_suggestions(self, word, max_suggestions=None):
        """Generate correction suggestions with caching - optimized for Sanskrit manual selection"""
        if max_suggestions is None:
            max_suggestions = self.max_suggestions
        
        word_lower = word.lower().strip()
        
        # Check cache first
        if word_lower in self.suggestion_cache:
            return self.suggestion_cache[word_lower][:max_suggestions]
        
        if self.is_word_correct(word):
            return []
        
        suggestions = []
        
        # Check confusion pairs first (HIGHEST priority - these are manually confirmed)
        confusion_correction = self.confusion_manager.get_correction(word_lower)
        if confusion_correction:
            suggestions.append(('HIGH', confusion_correction))
        
        # Use trie search for similar words
        trie_results = self.trie.search(word, self.max_edit_distance)
        
        # Sort by distance first, then alphabetically
        # Keep duplicates from confusion pairs out
        seen = {s[1] for s in suggestions}
        
        for distance, suggestion in sorted(trie_results, key=lambda x: (x[0], x[1])):
            if suggestion in seen:
                continue
            seen.add(suggestion)
            
            if distance == 1:
                confidence = 'HIGH'
            elif distance == 2:
                confidence = 'MEDIUM'
            else: 
                confidence = 'LOW'
            
            suggestions.append((confidence, suggestion))
        
        # Cache the result (cache ALL results, not limited)
        self.suggestion_cache[word_lower] = suggestions
        
        # Return limited results
        return suggestions[:max_suggestions]
    
    def detect_errors(self, text):
        """Detect errors in text"""
        if not text or not self.dictionary.words:
            return []
        
        words = self._tokenize(text)
        errors = []
        
        for i, word in enumerate(words):
            self.stats['words_checked'] += 1
            
            if not self.is_word_correct(word):
                self.stats['errors_found'] += 1
                suggestions = self.generate_suggestions(word)
                
                # Add error regardless of whether suggestions exist
                errors.append({
                    'word': word,
                    'position': i,
                    'suggestions': suggestions,
                    'confidence': suggestions[0][0] if suggestions else 'NONE'
                })
        
        return errors
    
    def auto_correct(self, text, confidence_threshold='HIGH'):
        """Auto-correct text while preserving spacing and format"""
        if not text or not self.dictionary.words:
            return text
        
        words = self._tokenize(text)
        corrected_words = []
        
        confidence_levels = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'NONE': 0}
        threshold_value = confidence_levels.get(confidence_threshold, 3)
        
        for word in words:
            if self.is_word_correct(word):
                corrected_words.append(word)
            else:
                suggestions = self.generate_suggestions(word, max_suggestions=1)
                
                if suggestions:
                    confidence, suggestion = suggestions[0]
                    conf_value = confidence_levels.get(confidence, 0)
                    
                    if conf_value >= threshold_value: 
                        corrected_words.append(suggestion)
                        self.stats['corrections_made'] += 1
                    else: 
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
        
        return ' '.join(corrected_words)
        
        for word in words:
            if self.is_word_correct(word):
                corrected_words.append(word)
            else:
                suggestions = self.generate_suggestions(word, max_suggestions=1)
                
                if suggestions:
                    confidence, suggestion = suggestions[0]
                    conf_value = confidence_levels.get(confidence, 0)
                    
                    if conf_value >= threshold_value: 
                        corrected_words. append(suggestion)
                        self.stats['corrections_made'] += 1
                    else: 
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def learn_from_correction(self, ocr_text, correct_text):
        """Learn from manual correction"""
        confusions = self.confusion_extractor.extract_from_texts(ocr_text, correct_text)
        
        for wrong, correct in confusions.items():
            self.confusion_manager.add_pair(wrong, correct)
        
        correct_words = self._tokenize(correct_text)
        for word in correct_words:
            if len(word) > 2 and not word.isdigit():
                self.dictionary.add_domain_word(word)
        
        # Only rebuild trie if we learned many new confusions
        if len(confusions) > 10:
            self._rebuild_trie()
        else:
            # Just clear cache for new confusions
            self.suggestion_cache.clear()
        
        return len(confusions)
    
    def _tokenize(self, text):
        """Tokenize text into words (supports Unicode/multi-byte characters)"""
        # For Devanagari and Unicode scripts, split by whitespace, punctuation, numbers
        # Don't use \b as it doesn't work well with Devanagari
        words = re.split(r'[\s\.,\!\?\-;:\(\)\[\]\{\}]+', text)
        # Remove empty strings and strip whitespace
        words = [w.strip() for w in words if w.strip()]
        return words
    
    def get_statistics(self):
        """Get statistics"""
        return self.stats. copy()
    
    def reset_statistics(self):
        """Reset statistics"""
        self.stats = {
            'words_checked': 0,
            'errors_found': 0,
            'corrections_made': 0
        }