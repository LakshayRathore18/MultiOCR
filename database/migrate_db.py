"""Update the document schema: python -m database.migrate_db."""
from database.db import get_db


def migrate_database():
    """Keep OCR/corrections intact and remove unused legacy metadata.

    Only obsolete columns are dropped. Their names below are retained solely
    so existing installations can be upgraded. No document rows are deleted.
    Repeating the migration is safe; all changes commit together.
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL lock_timeout = '5s'")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                image_path TEXT NOT NULL,
                ocr_text TEXT NOT NULL,
                corrected_text TEXT,
                cer FLOAT,
                status VARCHAR(20) DEFAULT 'ocr',
                ocr_embedding JSONB,
                text_embedding JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS ocr_embedding JSONB,
                ADD COLUMN IF NOT EXISTS text_embedding JSONB,
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                DROP COLUMN IF EXISTS image_hash,
                DROP COLUMN IF EXISTS parent_id,
                DROP COLUMN IF EXISTS version
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON documents(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON documents(created_at DESC)")
        conn.commit()
        print("Migration complete: original OCR, latest correction, embeddings and timestamps retained.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    migrate_database()
