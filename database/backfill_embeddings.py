"""Rebuild both document vectors: python -m database.backfill_embeddings."""
import argparse
import json

from database.db import get_db
from similarity.embeddings import embed_text, get_model


def backfill_embeddings(batch_size=50):
    """Recompute from source text, without changing text or document timestamps.

    Run migration first. Each update checks that both source texts are unchanged
    since reading. Repeating this command is safe and retries prior failures.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    # Fail before database writes if the model cannot be loaded.
    get_model()
    counts = {"updated": 0, "failed_embeddings": 0, "changed_during_run": 0}
    conn = get_db()
    cur = conn.cursor()
    last_id = 0
    try:
        while True:
            cur.execute("""
                SELECT id, ocr_text, corrected_text FROM documents
                WHERE id > %s ORDER BY id LIMIT %s
            """, (last_id, batch_size))
            rows = cur.fetchall()
            conn.commit()
            if not rows:
                break
            for doc_id, ocr_text, corrected_text in rows:
                vectors = []
                for source, text in (("raw", ocr_text), ("corrected", corrected_text)):
                    vector = None
                    if text and text.strip():
                        try:
                            vector = embed_text(text)
                            if vector is None:
                                raise ValueError("No vector generated for nonempty text")
                        except Exception as exc:
                            counts["failed_embeddings"] += 1
                            print(f"Document {doc_id}: {source} embedding failed ({type(exc).__name__})")
                    vectors.append(json.dumps(vector) if vector is not None else None)
                cur.execute("""
                    UPDATE documents SET ocr_embedding = %s, text_embedding = %s
                    WHERE id = %s
                      AND ocr_text IS NOT DISTINCT FROM %s
                      AND corrected_text IS NOT DISTINCT FROM %s
                """, (*vectors, doc_id, ocr_text, corrected_text))
                if cur.rowcount:
                    counts["updated"] += 1
                else:
                    counts["changed_during_run"] += 1
                conn.commit()
                last_id = doc_id
            print(f"Processed through document {last_id}: {counts}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    counts = backfill_embeddings(args.batch_size)
    print(f"Backfill complete: {counts}")
    return 1 if counts["failed_embeddings"] or counts["changed_during_run"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
