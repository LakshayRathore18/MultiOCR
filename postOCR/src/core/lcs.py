"""
Longest Common Subsequence for OCR confusion extraction
"""

from difflib import SequenceMatcher


class LCS:
    @staticmethod
    def extract_differences(ocr_text, correct_text):
        """Extract differences between OCR and correct text"""
        ocr_words = ocr_text.split()
        correct_words = correct_text.split()
        
        differences = []
        matcher = SequenceMatcher(None, ocr_words, correct_words)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                ocr_part = ' '.join(ocr_words[i1:i2])
                correct_part = ' '.join(correct_words[j1:j2])
                differences.append((ocr_part, correct_part, i1))
            elif tag == 'delete': 
                ocr_part = ' '.join(ocr_words[i1:i2])
                differences.append((ocr_part, '', i1))
            elif tag == 'insert':
                correct_part = ' '.join(correct_words[j1:j2])
                differences.append(('', correct_part, i1))
        
        return differences


class ConfusionExtractor:
    def __init__(self):
        self.confusions = {}
    
    def extract_from_texts(self, ocr_text, correct_text):
        """Extract confusion pairs from texts"""
        differences = LCS.extract_differences(ocr_text, correct_text)
        confusions = {}
        
        for ocr_part, correct_part, pos in differences:
            if ocr_part and correct_part:
                ocr_words = ocr_part.split()
                correct_words = correct_part.split()
                
                if len(ocr_words) == len(correct_words):
                    for ow, cw in zip(ocr_words, correct_words):
                        if ow != cw:
                            confusions[ow.lower()] = cw.lower()
                elif len(ocr_words) == 1 and len(correct_words) == 1:
                    confusions[ocr_words[0].lower()] = correct_words[0].lower()
        
        return confusions