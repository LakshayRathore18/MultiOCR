"""
File handling utilities
"""

import os
from pathlib import Path


class FileHandler:
    @staticmethod
    def read_file(filepath, encoding='utf-8'):
        """Read text file"""
        try:
            with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")
            return ""
    
    @staticmethod
    def write_file(filepath, content, encoding='utf-8'):
        """Write text file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e: 
            print(f"❌ Error writing {filepath}: {e}")
            return False
    
    @staticmethod
    def load_page_files(directory):
        """Load all page files from directory"""
        pages = {}
        path = Path(directory)
        
        if not path.exists():
            return pages
        
        for file in sorted(path.glob("page-*.txt")):
            page_num = int(file.stem.split('-')[1])
            content = FileHandler.read_file(file)
            pages[page_num] = content
        
        return pages
    
    @staticmethod
    def save_page_file(directory, page_num, content):
        """Save single page file"""
        filepath = Path(directory) / f"page-{page_num}.txt"
        return FileHandler.write_file(filepath, content)