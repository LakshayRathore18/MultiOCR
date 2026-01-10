"""
Trie-based edit distance for fast spell checking
"""

class TrieNode:
    def __init__(self):
        self.children = {}
        self.word = None
    
    def insert(self, word):
        node = self
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.word = word.lower()


class TrieEditDistance:
    def __init__(self):
        self.root = TrieNode()
        self.min_cost = float('inf')
    
    def insert_word(self, word):
        if word and len(word) > 1: 
            self.root.insert(word)
    
    def insert_words(self, words):
        for word in words:
            if word and len(word) > 1:
                self.insert_word(word)
    
    def search(self, word, max_cost=2):
        """Search for similar words with edit distance"""
        word = word.lower().strip()
        if len(word) < 2:
            return []
        
        results = []
        current_row = list(range(len(word) + 1))
        
        # Prune search space based on word length
        max_cost = min(max_cost, max(1, len(word) // 2 + 1))
        
        for char in self.root.children:
            self._search_recursive(
                self.root.children[char], 
                char, 
                word, 
                current_row, 
                results, 
                max_cost
            )
        
        # Sort by distance first, then alphabetically
        results.sort(key=lambda x: (x[0], x[1]))
        return results
    
    def _search_recursive(self, node, char, word, previous_row, results, max_cost):
        """Recursive trie search with pruning"""
        columns = len(word) + 1
        current_row = [previous_row[0] + 1]
        
        for col in range(1, columns):
            insert_cost = current_row[col - 1] + 1
            delete_cost = previous_row[col] + 1
            replace_cost = previous_row[col - 1]
            
            if word[col - 1] != char:
                replace_cost += 1
            
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        
        # Prune branches with costs too high
        min_row_cost = min(current_row)
        
        if node.word and current_row[-1] <= max_cost:
            results.append((current_row[-1], node.word))
        
        # Only continue if there's potential for good matches
        if min_row_cost <= max_cost:
            for char, child in node.children.items():
                self._search_recursive(child, char, word, current_row, results, max_cost)


def levenshtein_distance(s1, s2):
    """Simple Levenshtein distance calculation"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]