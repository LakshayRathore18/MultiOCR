"""
OCR Confusion Pairs Management
"""

from collections import defaultdict
import json
import os


class ConfusionPairManager:
    def __init__(self):
        self.pairs = {}
        self.frequency = defaultdict(int)
    
    def add_pair(self, wrong, correct, frequency=1):
        """Add confusion pair"""
        wrong = wrong.lower().strip()
        correct = correct.lower().strip()
        
        if not wrong or not correct or wrong == correct:
            return
        
        self.pairs[wrong] = correct
        self.frequency[(wrong, correct)] += frequency
    
    def get_correction(self, word):
        """Get correction for a word"""
        return self.pairs.get(word.lower())
    
    def load_from_file(self, filepath):
        """Load confusion pairs from file (tab-separated)"""
        if not os.path.exists(filepath):
            print(f"⚠️ Confusion file not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            wrong, correct = parts[0], parts[1]
                            freq = int(parts[2]) if len(parts) > 2 else 1
                            self.add_pair(wrong, correct, freq)
            print(f"✅ Loaded {len(self.pairs)} confusion pairs")
        except Exception as e: 
            print(f"❌ Error loading:  {e}")
    
    def save_to_file(self, filepath):
        """Save confusion pairs to file"""
        try: 
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                sorted_pairs = sorted(
                    self.pairs.items(),
                    key=lambda x: self.frequency.get((x[0], x[1]), 0),
                    reverse=True
                )
                
                for wrong, correct in sorted_pairs:
                    freq = self.frequency.get((wrong, correct), 1)
                    f.write(f"{wrong}\t{correct}\t{freq}\n")
            
            print(f"✅ Saved {len(self.pairs)} confusion pairs")
        except Exception as e: 
            print(f"❌ Error saving: {e}")
    
    def get_top_confusions(self, n=20):
        """Get top N most frequent confusions"""
        sorted_pairs = sorted(
            self.frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_pairs[:n]