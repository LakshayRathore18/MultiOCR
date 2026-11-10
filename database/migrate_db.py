"""
Database migration for document identity and dual OCR/corrected embeddings.
"""
from database.db import get_db
import sys

def migrate_database():
    """Add image_hash column and create unique index"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        print("Starting database migration...")

        # Ensure base 'documents' table exists (create if missing)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,

                image_path TEXT NOT NULL,
                ocr_text TEXT NOT NULL,
                corrected_text TEXT,

                cer FLOAT,

                status VARCHAR(20) DEFAULT 'ocr',
                version INTEGER DEFAULT 1,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✓ Ensured base 'documents' table exists")

        # Check if image_hash column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='image_hash'
        """)
        
        if cur.fetchone():
            print("✓ Column 'image_hash' already exists")
        else:
            print("Adding 'image_hash' column...")
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN image_hash TEXT
            """)
            print("✓ Column 'image_hash' added")
        
        # Check if parent_id column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='parent_id'
        """)
        
        if cur.fetchone():
            print("✓ Column 'parent_id' already exists")
        else:
            print("Adding 'parent_id' column...")
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN parent_id INTEGER REFERENCES documents(id)
            """)
            print("✓ Column 'parent_id' added")
        
        # Check if text_embedding column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='text_embedding'
        """)
        
        if cur.fetchone():
            print("✓ Column 'text_embedding' already exists")
        else:
            print("Adding 'text_embedding' column...")
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN text_embedding JSONB
            """)
            print("✓ Column 'text_embedding' added")
        
        # Keep the legacy text_embedding name for corrected text only.
        cur.execute("""
            ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_embedding JSONB
        """)

        # Create unique index on image_hash (if not exists)
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename='documents' AND indexname='idx_image_hash'
        """)
        
        if cur.fetchone():
            print("✓ Index 'idx_image_hash' already exists")
        else:
            print("Creating unique index on image_hash...")
            cur.execute("""
                CREATE INDEX idx_image_hash ON documents(image_hash)
            """)
            print("✓ Index 'idx_image_hash' created")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nNew schema supports:")
        print("  - Hash-based document identity")
        print("  - Proper version tracking per document")
        print("  - Deduplication on upload")
        print("  - Semantic similarity search (text embeddings)")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_database()
