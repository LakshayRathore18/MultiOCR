"""
Test script to verify hash-based document identity system
"""
from utils.image_hash import compute_image_hash_from_file
from database.db import get_db
import os

def test_hash_system():
    """Test the hash-based document identity system"""
    
    print("\n" + "=" * 60)
    print("TESTING HASH-BASED DOCUMENT IDENTITY SYSTEM")
    print("=" * 60)
    
    # Check if test image exists
    test_images = [
        "ocr_env/images/manu2.jpg",
        "uploads"
    ]
    
    # Find first available test image
    test_image = None
    for path in test_images:
        if os.path.exists(path):
            if os.path.isdir(path):
                # Get first image from uploads
                files = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if files:
                    test_image = os.path.join(path, files[0])
                    break
            else:
                test_image = path
                break
    
    if not test_image:
        print("\n⚠️  No test images found. Upload an image first.")
        return
    
    print(f"\n1️⃣  Testing with: {test_image}")
    
    # Compute hash
    image_hash = compute_image_hash_from_file(test_image)
    print(f"\n2️⃣  Image hash computed: {image_hash[:16]}...{image_hash[-8:]}")
    
    # Check database
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Check if image_hash column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='image_hash'
        """)
        
        if not cur.fetchone():
            print("\n❌ Database not migrated! Run: python migrate_db.py")
            conn.close()
            return
        
        print("\n3️⃣  Database schema: ✓ image_hash column exists")
        
        # Find documents with this hash
        cur.execute(
            """SELECT id, version, status, cer, created_at 
               FROM documents 
               WHERE image_hash = %s 
               ORDER BY version ASC""",
            (image_hash,)
        )
        
        versions = cur.fetchall()
        
        if versions:
            print(f"\n4️⃣  Found {len(versions)} version(s) of this document:")
            print("\n" + "-" * 60)
            print(f"{'Doc ID':<10} {'Version':<10} {'Status':<15} {'CER':<10} {'Created'}")
            print("-" * 60)
            
            for doc_id, version, status, cer, created_at in versions:
                cer_str = f"{cer:.4f}" if cer else "N/A"
                created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
                print(f"{doc_id:<10} {version:<10} {status:<15} {cer_str:<10} {created_str}")
            
            print("-" * 60)
            
            # Get latest version
            latest = versions[-1]
            print(f"\n5️⃣  Latest version: v{latest[1]} ({latest[2]})")
            
            if latest[3]:  # has CER
                print(f"    Character Error Rate: {latest[3]:.4f}")
                
        else:
            print("\n4️⃣  This is a NEW document (not in database yet)")
            print("    → Upload it via the web interface to create entry")
        
        # Show total documents in DB
        cur.execute("SELECT COUNT(DISTINCT image_hash) FROM documents WHERE image_hash IS NOT NULL")
        unique_docs = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM documents")
        total_versions = cur.fetchone()[0]
        
        print(f"\n6️⃣  Database statistics:")
        print(f"    Unique documents: {unique_docs}")
        print(f"    Total versions: {total_versions}")
        print(f"    Avg versions per doc: {total_versions/unique_docs if unique_docs > 0 else 0:.1f}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ HASH SYSTEM TEST COMPLETE")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("    Make sure PostgreSQL is running and credentials are correct.")

if __name__ == "__main__":
    test_hash_system()
