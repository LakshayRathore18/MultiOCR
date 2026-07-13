"""
Export training data from PostgreSQL database to train.json
Extracts ocr_text and corrected_text pairs from documents table
"""
import json
import sys
import os

# Add parent directory to path to import db module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db


def export_training_data(output_file='train.json'):
    """
    Export OCR text and corrected text pairs from database to JSON file.
    Only exports documents that have both ocr_text and corrected_text.
    """
    conn = get_db()
    cur = conn.cursor()
    
    try:
        print("Fetching documents from database...")
        
        # Query documents that have both OCR and corrected text
        cur.execute("""
            SELECT 
                id,
                ocr_text,
                corrected_text,
                image_path
            FROM documents
            WHERE corrected_text IS NOT NULL 
            AND corrected_text != ''
            AND ocr_text IS NOT NULL
            AND ocr_text != ''
            ORDER BY id
        """)
        
        rows = cur.fetchall()
        
        if not rows:
            print("⚠️  No documents with corrected text found in database.")
            return
        
        # Format training data
        training_data = []
        for row in rows:
            doc_id, ocr_text, corrected_text, image_path = row
            training_data.append({
                "ocr_text": ocr_text,
                "corrected_text": corrected_text
            })
        
        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Successfully exported {len(training_data)} document pairs to {output_file}")
        print(f"   Total characters in OCR text: {sum(len(d['ocr_text']) for d in training_data)}")
        print(f"   Total characters in corrected text: {sum(len(d['corrected_text']) for d in training_data)}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    # Default output file in parent directory
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'train.json'
    )
    
    export_training_data(output_path)
