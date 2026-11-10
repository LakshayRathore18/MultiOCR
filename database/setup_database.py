"""
Complete Database Setup Script
Creates all necessary tables and indexes for the MultiOCR application
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

def get_db_config():
    """Get database configuration from environment"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'multiocrdb'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }

def setup_database():
    """Create database and all tables"""
    config = get_db_config()
    
    print("="*60)
    print("🗄️  MultiOCR Database Setup")
    print("="*60)
    print(f"Host: {config['host']}:{config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print("="*60)
    
    try:
        # Connect without database to create it if needed
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{config['database']}'")
        if not cur.fetchone():
            print(f"\n📁 Creating database '{config['database']}'...")
            cur.execute(f"CREATE DATABASE {config['database']}")
            print(f"✅ Database '{config['database']}' created!")
        else:
            print(f"\n✓ Database '{config['database']}' already exists")
        
        cur.close()
        conn.close()
        
        # Connect to the target database
        conn = psycopg2.connect(**config)
        cur = conn.cursor()
        
        print("\n📋 Creating tables...")
        
        # Create documents table with all columns in one go
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                
                -- File information
                image_path TEXT NOT NULL,
                
                -- OCR results
                ocr_text TEXT NOT NULL,
                corrected_text TEXT,
                
                -- Quality metrics
                cer FLOAT,
                
                -- Review state
                status VARCHAR(20) DEFAULT 'ocr' CHECK (status IN ('pending', 'ocr', 'corrected', 'reviewed')),
                
                -- Similarity search
                ocr_embedding JSONB,  -- Original, uncorrected OCR
                text_embedding JSONB, -- Saved corrected text only
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✓ documents table created")
        
        # Create indexes for better performance
        print("\n🔍 Creating indexes...")
        
        indexes = [
            ("idx_status", "documents", "status", "Status filtering"),
            ("idx_created_at", "documents", "created_at DESC", "Time-based sorting"),
        ]
        
        for idx_name, table, column, description in indexes:
            cur.execute(f"""
                SELECT 1 FROM pg_indexes 
                WHERE tablename='{table}' AND indexname='{idx_name}'
            """)
            if not cur.fetchone():
                cur.execute(f"CREATE INDEX {idx_name} ON {table}({column})")
                print(f"  ✓ {idx_name} - {description}")
            else:
                print(f"  ✓ {idx_name} already exists")
        
        # Create trigger for updated_at timestamp
        print("\n⚙️  Creating triggers...")
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        
        cur.execute("""
            DROP TRIGGER IF EXISTS update_documents_updated_at ON documents
        """)
        
        cur.execute("""
            CREATE TRIGGER update_documents_updated_at
            BEFORE UPDATE ON documents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """)
        print("  ✓ Auto-update timestamp trigger created")
        
        conn.commit()
        
        # Verify setup
        print("\n🔍 Verifying setup...")
        cur.execute("SELECT COUNT(*) FROM documents")
        count = cur.fetchone()[0]
        print(f"  ✓ Documents table accessible ({count} rows)")
        
        print("\n" + "="*60)
        print("✅ Database setup completed successfully!")
        print("="*60)
        print("\n📊 Schema Features:")
        print("  • Original OCR and latest saved correction")
        print("  • CER tracking for accuracy measurement")
        print("  • Status workflow (pending → ocr → corrected → reviewed)")
        print("  • Text embeddings for similarity search")
        print("  • Auto-updating timestamps")
        print("\n🚀 You can now start the application!")
        print("="*60)
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_database()
