"""
Dictionary management for spell checking
"""

import os


class Dictionary:
    def __init__(self):
        self.words = set()
        self.domain_words = set()
        self.positive_words = set()
        self.language = "english"
    
    def load_from_file(self, filepath, encoding='utf-8'):
        """Load dictionary from file"""
        if not os.path.exists(filepath):
            print(f"⚠️ Dictionary file not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                words = set(line.strip().lower() for line in f if line.strip())
                self.words.update(words)
            
            print(f"✅ Loaded {len(self.words)} dictionary words")
            return True
        except Exception as e:
            print(f"❌ Error loading dictionary: {e}")
            return False
    
    def contains(self, word):
        """Check if word exists in any dictionary"""
        word_lower = word.lower().strip()
        return (word_lower in self.words or 
                word_lower in self.domain_words or
                word_lower in self.positive_words)
    
    def add_word(self, word):
        """Add word to dictionary"""
        if word: 
            self.words.add(word.lower().strip())
    
    def add_domain_word(self, word):
        """Add domain-specific word"""
        if word: 
            self.domain_words.add(word.lower().strip())
    
    def add_domain_words(self, words):
        """Add multiple domain words"""
        if isinstance(words, str):
            words = words.split()
        self.domain_words.update(w.lower().strip() for w in words if w)
    
    def save_domain_words(self, filepath):
        """Save domain words to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                for word in sorted(self.domain_words):
                    f.write(f"{word}\n")
            print(f"✅ Saved {len(self.domain_words)} domain words")
        except Exception as e:
            print(f"❌ Error saving: {e}")
    
    def load_domain_words(self, filepath):
        """Load domain words from file"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self.domain_words = set(line.strip().lower() for line in f if line.strip())
            print(f"✅ Loaded {len(self.domain_words)} domain words")
    
    def get_statistics(self):
        """Get dictionary statistics"""
        return {
            'total_words': len(self.words),
            'domain_words':  len(self.domain_words),
            'positive_words': len(self.positive_words),
            'language': self.language
        }