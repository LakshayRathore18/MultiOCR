"""Dual-search and save regressions; no OCR/model downloads or database writes."""
import importlib
import json
import sys
import types
import unittest
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock, patch

from jinja2 import Environment, FileSystemLoader, select_autoescape

from database import backfill_embeddings as backfill
from database import migrate_db
from similarity import embeddings, search


ROOT = Path(__file__).resolve().parents[1]
EDIT_TIME = datetime(2026, 11, 10, 12, 30)


def document(doc_id=1, raw="old raw", corrected="old correction",
             raw_vector=None, corrected_vector=None):
    return (doc_id, corrected, raw, "uploads/example.png", 0.0, "corrected", EDIT_TIME,
            corrected_vector, raw_vector)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.conn = Mock()
        self.cur = self.conn.cursor.return_value
        self.db = patch.object(search, "get_db", return_value=self.conn)
        self.db.start()
        self.addCleanup(self.db.stop)

    def find(self, rows, **kwargs):
        self.cur.fetchall.return_value = rows
        return search.find_similar_documents(
            current_text="new raw", current_embedding=[1, 0], **kwargs)

    def test_either_source_wins_and_both_texts_always_return(self):
        rows = [document(1, raw_vector=[1, 0], corrected_vector=[0, 1]),
                document(2, raw_vector=[0, 1], corrected_vector='[1, 0]')]
        results = self.find(rows)
        self.assertEqual([r["matched_on"] for r in results], ["raw", "corrected"])
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result["ocr_text"], "old raw")
            self.assertEqual(result["corrected_text"], "old correction")
            self.assertEqual(result["cer"], 0)
            self.assertEqual(result["similarity_method"], "cosine")
        self.cur.close.assert_called_once()
        self.conn.close.assert_called_once()

    def test_tie_prefers_raw_and_returns_one_record(self):
        result = self.find([document(raw_vector=[1, 0], corrected_vector=[1, 0])])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["matched_on"], "raw")

    def test_threshold_sort_limit_and_exclusion(self):
        rows = [document(3, raw_vector=[0, 1]),
                document(2, corrected_vector=[0.8, 0.6]),
                document(1, raw_vector=[1, 0])]
        self.assertEqual([r["doc_id"] for r in self.find(rows, limit=1, current_doc_id=9)], [1])
        query, params = self.cur.execute.call_args.args
        self.assertIn("WHERE id != %s", query)
        self.assertIn("LIMIT 100", query)
        self.assertEqual(params, (9,))
        self.assertEqual([r["doc_id"] for r in self.find(rows, threshold=0.9)], [1])

    def test_invalid_vectors_use_both_texts_for_fallback(self):
        for invalid in (None, "bad json", [], [0, 0], [1, 0, 0],
                        [float("nan"), 0], [float("inf"), 0], [[1, 0]]):
            with self.subTest(vector=invalid):
                result = self.find([document(raw="new raw", raw_vector=invalid)])
                self.assertEqual(result[0]["similarity_method"], "jaccard")
                self.assertEqual(result[0]["matched_on"], "raw")
        result = self.find([document(corrected="new raw")])
        self.assertEqual(result[0]["matched_on"], "corrected")

    def test_valid_vector_is_not_mixed_with_word_overlap(self):
        result = self.find([document(raw="new raw", corrected_vector=[0.8, 0.6])])
        self.assertIsNone(result[0]["raw_score"])
        self.assertEqual(result[0]["matched_on"], "corrected")
        self.assertEqual(result[0]["score"], 0.8)

    def test_missing_correction_ignores_stray_corrected_vector(self):
        result = self.find([document(raw="new raw", corrected=" ", corrected_vector=[1, 0])])
        self.assertIsNone(result[0]["corrected_text"])
        self.assertIsNone(result[0]["corrected_score"])
        self.assertFalse(result[0]["has_correction"])

    def test_disabled_embeddings_and_empty_query(self):
        result = self.find([document(raw="new raw", raw_vector=[0, 1])], use_embeddings=False)
        self.assertEqual(result[0]["similarity_method"], "jaccard")
        self.assertEqual(search.find_similar_documents(" "), [])

    def test_query_is_embedded_once(self):
        self.cur.fetchall.return_value = [document(raw_vector=[1, 0])]
        with patch.object(embeddings, "embed_text", return_value=[1, 0]) as embed:
            self.assertEqual(len(search.find_similar_documents("raw query")), 1)
        embed.assert_called_once_with("raw query")


class SaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import the actual routes without importing heavyweight OCR wrappers.
        wrappers = {}
        for name, functions in {
            "ocr.paddle_ocr": ("run_paddleocr", "init_paddle_model"),
            "ocr.easy_ocr": ("run_easyocr", "init_easy_model"),
            "ocr.deepseek_ocr": ("run_deepseek", "init_deepseek_model"),
        }.items():
            module = types.ModuleType(name)
            for function in functions:
                setattr(module, function, Mock())
            wrappers[name] = module
        cls.modules = patch.dict(sys.modules, wrappers)
        cls.modules.start()
        cls.app = importlib.import_module("web.app")

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def setUp(self):
        self.conn = Mock()
        self.cur = self.conn.cursor.return_value
        self.db = patch.object(self.app, "get_db", return_value=self.conn)
        self.db.start()
        self.addCleanup(self.db.stop)
        self.request = types.SimpleNamespace(session={})
        self.data = self.app.SaveCorrectionRequest(corrected_text="saved correction")

    def test_new_save_pairs_both_vectors_with_original_and_correction(self):
        self.cur.fetchone.return_value = (42, EDIT_TIME)
        with patch.dict(self.app.TEMP_SESSION_STORE, {
            "current_filepath": "uploads/example.png",
            "current_ocr_results": {"full_text": "original OCR"},
        }), patch.object(self.app, "safe_embed_text", side_effect=[[1, 0], [0, 1]]) as embed:
            result = self.app.review_new_post(self.request, self.data)
            restored = self.app.TEMP_SESSION_STORE['current_ocr_results']
            self.assertEqual(restored['full_text'], 'original OCR')
            self.assertTrue(restored['has_correction'])
            self.assertEqual(restored['updated_at'], EDIT_TIME.isoformat())
        self.assertEqual(result["doc_id"], 42)
        self.assertTrue(result['has_correction'])
        self.assertEqual(result['status'], 'corrected')
        self.assertEqual(result['updated_at'], EDIT_TIME.isoformat())
        self.assertEqual([c.args[0] for c in embed.call_args_list], ["original OCR", "saved correction"])
        params = self.cur.execute.call_args.args[1]
        self.assertEqual(params[1:3], ("original OCR", "saved correction"))
        self.assertEqual(json.loads(params[3]), [1, 0])
        self.assertEqual(json.loads(params[4]), [0, 1])

    def test_manual_edit_refreshes_correction_only_and_failure_clears_vector(self):
        for vector in ([0, 1], None):
            with self.subTest(vector=vector):
                self.cur.fetchone.side_effect = [("original OCR",), (EDIT_TIME,)]
                with patch.object(self.app, "safe_embed_text", return_value=vector) as embed:
                    result = self.app.review_post(self.request, 42, self.data)
                self.assertEqual(result['updated_at'], EDIT_TIME.isoformat())
                self.assertTrue(result['has_correction'])
                embed.assert_called_once_with("saved correction")
                sql, params = self.cur.execute.call_args.args
                self.assertNotIn("ocr_embedding", sql)
                self.assertNotIn("ocr_text=", sql)
                self.assertEqual(params[2], json.dumps(vector) if vector is not None else None)

    def test_auto_correction_refreshes_embedding_without_changing_raw(self):
        self.cur.fetchone.return_value = (EDIT_TIME,)
        integration = types.ModuleType("postocr_integration")
        integration.correct_text = Mock(return_value={"success": True, "corrected_text": "auto correction"})
        for vector in ([0, 1], None):
            with self.subTest(vector=vector), patch.dict(sys.modules, {"postocr_integration": integration}), \
                    patch.object(self.app, "safe_embed_text", return_value=vector) as embed:
                result = self.app.correct_ocr(self.app.CorrectRequest(text="edited input", doc_id=42))
                self.assertTrue(result["success"])
                self.assertEqual(result['updated_at'], EDIT_TIME.isoformat())
                embed.assert_called_once_with("auto correction")
                sql, params = self.cur.execute.call_args.args
                self.assertIn("text_embedding = %s", sql)
                self.assertNotIn("ocr_embedding", sql)
                self.assertEqual(params[2], json.dumps(vector) if vector is not None else None)

    def test_existing_review_search_uses_original_even_when_corrected(self):
        self.cur.fetchone.return_value = ("uploads/example.png", "original OCR", "saved correction",
                                         0.0, "corrected", EDIT_TIME)
        with patch.object(self.app, "find_similar_documents", return_value=[]) as find, \
                patch.object(self.app.templates, "TemplateResponse"):
            self.app.review_get(self.request, 42)
        self.assertEqual(find.call_args.kwargs["current_text"], "original OCR")

    def test_edit_metadata_updates_only_the_matching_active_draft(self):
        with patch.dict(self.app.TEMP_SESSION_STORE, {
            'current_doc_id': 42, 'current_status': 'processed',
            'current_ocr_results': {'full_text': 'original OCR'},
        }):
            self.app.saved_correction_metadata(7, EDIT_TIME, 0.1)
            self.assertEqual(self.app.TEMP_SESSION_STORE['current_status'], 'processed')
            self.app.saved_correction_metadata(42, EDIT_TIME, 0)
            restored = self.app.get_session_data(self.request)['ocr_results']
            self.assertEqual(restored['full_text'], 'original OCR')
            self.assertTrue(restored['has_correction'])
            self.assertEqual(restored['updated_at'], EDIT_TIME.isoformat())
            self.assertEqual(restored['cer'], 0)

    def test_auto_fix_missing_document_does_not_claim_a_save(self):
        integration = types.ModuleType('postocr_integration')
        integration.correct_text = Mock(return_value={'success': True, 'corrected_text': 'fixed'})
        self.cur.fetchone.return_value = None
        with patch.dict(sys.modules, {'postocr_integration': integration}), \
                patch.object(self.app, 'safe_embed_text', return_value=[1, 0]):
            result = self.app.correct_ocr(self.app.CorrectRequest(text='raw', doc_id=404))
        self.assertEqual(result.status_code, 404)
        self.conn.commit.assert_not_called()

    def test_new_ocr_is_preserved_and_previous_correction_is_reference_only(self):
        raw = "the studcnt reads"
        corrected = "the student reads"
        reference = dict(doc_id=42, ocr_text=raw, corrected_text=corrected)
        # This stored correction would pass the former 85% replacement rule.
        benchmark = dict(results=[dict(text=raw, confidence=0.8)],
                         time_sec=0.1, lines=1, avg_confidence=0.8)
        for mode, model_name in (("paddleocr", "paddle_model"),
                                 ("easyocr", "easy_model"),
                                 ("deepseek", "deepseek_model")):
            with self.subTest(mode=mode), \
                    patch.dict(self.app.TEMP_SESSION_STORE, {
                        "current_doc_id": 42, "current_status": "corrected",
                        "current_ocr_results": {"full_text": corrected},
                    }), patch.object(self.app.os.path, "exists", return_value=True), \
                    patch.object(self.app, model_name, object()), \
                    patch.object(self.app, "benchmark_ocr", return_value=benchmark), \
                    patch.object(self.app, "validate_ocr_text", return_value={
                        "quality_score": 1.0, "issues": [], "devanagari_chars": 0,
                    }), patch.object(self.app, "find_similar_documents", return_value=[reference]) as find, \
                    patch.object(self.app.templates, "TemplateResponse") as render:
                result = self.app.process_ocr(self.request, self.app.ProcessRequest(
                    filepath="uploads/new.png", mode=mode))
                self.assertTrue(result["success"])
                self.assertEqual(result["full_text"], raw)
                self.assertEqual(result["text"][0]["text"], raw)
                self.assertEqual(result["text"][0]["confidence"], 0.8)
                self.assertEqual(result['status'], 'ocr')
                self.assertFalse(result['has_correction'])
                self.assertIsNone(result['updated_at'])
                self.assertIsNone(result["doc_id"])
                self.assertNotIn("cer", result)
                self.assertIsNone(self.app.TEMP_SESSION_STORE["current_doc_id"])
                self.assertEqual(self.app.TEMP_SESSION_STORE["current_ocr_results"]["full_text"], raw)
                self.app.get_db.assert_not_called()
                self.app.review_new_get(self.request)
                self.assertEqual(find.call_args.kwargs["current_text"], raw)
                context = render.call_args.args[1]
                self.assertEqual(context["ocr_text"], raw)
                self.assertIsNone(context["corrected_text"])
                self.assertEqual(context["similar_docs"], [reference])

    def test_home_search_returns_paired_references_without_replacing_output(self):
        reference = dict(doc_id=42, ocr_text="old raw", corrected_text="old correction")
        with patch.dict(self.app.TEMP_SESSION_STORE, {"current_ocr_results": {"full_text": "fresh OCR"}}), \
                patch.object(self.app, "find_similar_documents", return_value=[reference]) as find:
            result = self.app.similar_documents(self.app.SimilarDocumentsRequest(text="fresh OCR", doc_id=7))
            self.assertEqual(result, {"success": True, "similar_docs": [reference]})
            find.assert_called_once_with(current_text="fresh OCR", current_doc_id=7, threshold=0.3, limit=100)
            self.assertEqual(self.app.TEMP_SESSION_STORE["current_ocr_results"]["full_text"], "fresh OCR")
            self.app.get_db.assert_not_called()

    def test_home_search_empty_text_and_failure(self):
        with patch.object(self.app, "find_similar_documents", side_effect=RuntimeError("search offline")) as find:
            empty = self.app.similar_documents(self.app.SimilarDocumentsRequest(text=" "))
            self.assertEqual(empty, {"success": True, "similar_docs": []})
            find.assert_not_called()
            response = self.app.similar_documents(self.app.SimilarDocumentsRequest(text="fresh OCR"))
            self.assertEqual(response.status_code, 503)
            self.assertFalse(json.loads(response.body)["success"])


class ButtonParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.copy_texts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "data-text" in attrs:
            self.copy_texts.append(attrs["data-text"])


class DisplayTests(unittest.TestCase):
    def test_review_displays_real_save_information(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'web/templates'), autoescape=select_autoescape())
        template = env.get_template('review_new.html')
        for saved in (None, 'saved correction'):
            html = template.render(url_for=lambda *a, **k: '/static/example',
                                   doc_id='new' if saved is None else 42, image_path='example.png',
                                   ocr_text='original', corrected_text=saved, cer=None,
                                   updated_at=EDIT_TIME if saved else None, similar_docs=[])
            if saved:
                self.assertIn('Correction saved', html)
                self.assertIn('Last edited: 2026-11-10 12:30', html)
            else:
                self.assertIn('Not saved yet', html)

    def test_home_template_places_references_after_output(self):
        env = Environment(loader=FileSystemLoader(ROOT / "web/templates"), autoescape=select_autoescape())
        html = env.get_template("index.html").render(url_for=lambda name, path: f"/static/{path}")
        self.assertLess(html.index('id="fullText"'), html.index('id="similarDocuments"'))
        self.assertLess(html.index('similar_documents.js'), html.index('static/script.js'))

        class PlacementParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.reference_parents = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get("id") == "similarDocuments":
                    self.reference_parents = [entry[1].get("class", "") for entry in self.stack]
                if tag not in {"meta", "link", "input", "img", "br", "hr"}:
                    self.stack.append((tag, attrs))

            def handle_endtag(self, tag):
                if self.stack and self.stack[-1][0] == tag:
                    self.stack.pop()

        placement = PlacementParser()
        placement.feed(html)
        self.assertIn("container", placement.reference_parents)
        self.assertNotIn("main-content", placement.reference_parents)
        self.assertNotIn("right-panel", placement.reference_parents)
        self.assertIn('id="moreSimilarDocuments"', html)

    def test_both_sources_and_full_copy_text_for_either_match(self):
        env = Environment(loader=FileSystemLoader(ROOT / "web/templates"), autoescape=select_autoescape())
        template = env.get_template("review_new.html")
        raw = 'धर्म "OCR"\n<script>raw</script>'
        corrected = 'धर्मः "corrected"\n<script>saved</script>'
        for source in ("raw", "corrected"):
            for saved in (corrected, None):
                with self.subTest(source=source, saved=saved):
                    doc = dict(doc_id=42, score=0.9, status="corrected", matched_on=source,
                               similarity_method="cosine", ocr_text=raw, corrected_text=saved)
                    html = template.render(url_for=lambda *a, **k: "/static/review_new.css",
                                           doc_id="new", image_path="example.png", ocr_text="current",
                                           corrected_text=None, cer=None, updated_at=None, similar_docs=[doc])
                    panel = html.split("<!-- Similar Documents Panel -->")[1]
                    self.assertIn("Original OCR</h3>", panel)
                    self.assertIn("Saved Correction</h3>", panel)
                    self.assertNotIn("<script>raw</script>", panel)
                    self.assertNotIn("<script>saved</script>", panel)
                    parser = ButtonParser()
                    parser.feed(panel)
                    self.assertEqual(parser.copy_texts, [raw, saved] if saved else [raw])
                    if not saved:
                        self.assertIn("No saved correction", panel)


class MigrationTests(unittest.TestCase):
    def test_migration_commits_schema_changes_without_deleting_documents(self):
        conn = Mock()
        with patch.object(migrate_db, 'get_db', return_value=conn):
            migrate_db.migrate_database()
        sql = '\n'.join(call.args[0] for call in conn.cursor.return_value.execute.call_args_list)
        self.assertIn('DROP COLUMN IF EXISTS', sql)
        self.assertIn('ADD COLUMN IF NOT EXISTS ocr_embedding', sql)
        self.assertNotIn('DELETE FROM', sql)
        self.assertNotIn('CASCADE', sql)
        conn.commit.assert_called_once()
        conn.cursor.return_value.close.assert_called_once()
        conn.close.assert_called_once()

    def test_failed_cleanup_rolls_back_and_closes_connection(self):
        conn = Mock()
        conn.cursor.return_value.execute.side_effect = RuntimeError('dependency prevents cleanup')
        with patch.object(migrate_db, 'get_db', return_value=conn):
            with self.assertRaises(RuntimeError):
                migrate_db.migrate_database()
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()


class BackfillTests(unittest.TestCase):
    def test_rebuilds_from_sources_skips_empty_and_guards_concurrent_edits(self):
        conn = Mock()
        cur = conn.cursor.return_value
        cur.fetchall.side_effect = [[(1, "raw", "saved"), (2, "raw only", None)], []]
        cur.rowcount = 1
        with patch.object(backfill, "get_model"), patch.object(backfill, "get_db", return_value=conn), \
                patch.object(backfill, "embed_text", side_effect=[[1, 0], [0, 1], [0.5, 0.5]]) as embed:
            counts = backfill.backfill_embeddings()
        self.assertEqual(counts["updated"], 2)
        self.assertEqual([c.args[0] for c in embed.call_args_list], ["raw", "saved", "raw only"])
        updates = [c.args for c in cur.execute.call_args_list if "UPDATE documents" in c.args[0]]
        self.assertEqual(json.loads(updates[0][1][0]), [1, 0])
        self.assertEqual(json.loads(updates[0][1][1]), [0, 1])
        self.assertIsNone(updates[1][1][1])
        self.assertIn("corrected_text IS NOT DISTINCT FROM %s", updates[0][0])
        self.assertNotIn("updated_at", updates[0][0])

    def test_failed_vector_is_cleared_and_concurrent_change_reported(self):
        conn = Mock()
        cur = conn.cursor.return_value
        cur.fetchall.side_effect = [[(1, "raw", "saved")], []]
        cur.rowcount = 0
        with patch.object(backfill, "get_model"), patch.object(backfill, "get_db", return_value=conn), \
                patch.object(backfill, "embed_text", side_effect=[[1, 0], RuntimeError("failed")]):
            counts = backfill.backfill_embeddings()
        self.assertEqual(counts["failed_embeddings"], 1)
        self.assertEqual(counts["changed_during_run"], 1)
        update = [c for c in cur.execute.call_args_list if "UPDATE documents" in c.args[0]][0]
        self.assertIsNone(update.args[1][1])

    def test_model_failure_stops_before_database_access(self):
        with patch.object(backfill, "get_model", side_effect=RuntimeError("missing model")), \
                patch.object(backfill, "get_db") as db:
            with self.assertRaises(RuntimeError):
                backfill.backfill_embeddings()
        db.assert_not_called()

    def test_safe_embedding_returns_none_on_failure(self):
        with patch.object(embeddings, "embed_text", side_effect=RuntimeError("failed")), \
                self.assertLogs("similarity.embeddings", level="ERROR"):
            self.assertIsNone(embeddings.safe_embed_text("text"))


if __name__ == "__main__":
    unittest.main()
