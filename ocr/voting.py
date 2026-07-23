"""
ocr/voting.py  -  Ensemble OCR Voting Engine
=============================================

Strategy
--------
1. Edge-case guard  - if one engine produced 0 lines, return the other's
   results immediately (no point voting against nothing).
2. Normalize        - clean Devanagari text from every line before comparing.
3. Align lines      - use SequenceMatcher to match lines by *content* instead
   of by index, so a 10-line Paddle output is correctly paired with a 12-line
   DeepSeek output even when they segment differently.
4. Vote per pair    -
     Both engines see this line -> word-level vote, weighted confidence.
     Only one engine sees it    -> accept if confidence >= threshold.
5. Confidence gate  - drop any final line whose merged confidence is below
   min_confidence.
"""

from difflib import SequenceMatcher
from ocr.normalize import normalize_text


# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------

def _norm_list(lst: list) -> list:
    """Normalize text in every item and drop blank lines."""
    out = []
    for item in lst:
        item["text"] = normalize_text(item.get("text", "") or "")
        if item["text"].strip():
            out.append(item)
    return out


def _weighted_confidence(conf_a: float, conf_b: float) -> float:
    """
    Compute an ensemble confidence score that rewards agreement.

    Formula: weighted average where each weight is the engine's own confidence.
        merged = (conf_a^2 + conf_b^2) / (conf_a + conf_b)

    This is naturally higher when both engines are confident, and lower when
    one engine is unsure - more honest than a raw max().
    """
    denom = conf_a + conf_b
    if denom == 0:
        return 0.0
    return (conf_a ** 2 + conf_b ** 2) / denom


def _word_level_vote(text_a: str, conf_a: float,
                     text_b: str, conf_b: float) -> str:
    """
    Merge two OCR lines at the word level.

    - Words both engines agree on  -> keep them (strongest signal).
    - Words that differ            -> pick from the higher-confidence engine.
    - Words only one engine has    -> include only if that engine's confidence
                                      is >= 0.75 to avoid hallucinations.
    """
    words_a = text_a.split()
    words_b = text_b.split()

    if not words_a:
        return text_b
    if not words_b:
        return text_a

    result_words = []
    matcher = SequenceMatcher(None, words_a, words_b, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result_words.extend(words_a[i1:i2])
        elif tag == "replace":
            if conf_a >= conf_b:
                result_words.extend(words_a[i1:i2])
            else:
                result_words.extend(words_b[j1:j2])
        elif tag == "delete":          # words only in A (Paddle)
            if conf_a >= 0.75:
                result_words.extend(words_a[i1:i2])
        elif tag == "insert":          # words only in B (DeepSeek)
            if conf_b >= 0.75:
                result_words.extend(words_b[j1:j2])

    return " ".join(result_words)


def _align_lines(list_a: list, list_b: list) -> list:
    """
    Align two lists of OCR line dicts by text similarity instead of by index.

    Uses SequenceMatcher on the text content to find which lines correspond
    across the two engines, even when line counts differ.

    Returns a list of (a_item | None, b_item | None) pairs.
    """
    texts_a = [l["text"] for l in list_a]
    texts_b = [l["text"] for l in list_b]

    matcher = SequenceMatcher(None, texts_a, texts_b, autojunk=False)
    pairs = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        seg_a = list_a[i1:i2]
        seg_b = list_b[j1:j2]

        if tag == "equal":
            for a, b in zip(seg_a, seg_b):
                pairs.append((a, b))

        elif tag == "replace":
            # Pair what we can; leave the rest unmatched
            min_len = min(len(seg_a), len(seg_b))
            for a, b in zip(seg_a[:min_len], seg_b[:min_len]):
                pairs.append((a, b))
            for a in seg_a[min_len:]:
                pairs.append((a, None))
            for b in seg_b[min_len:]:
                pairs.append((None, b))

        elif tag == "delete":
            for a in seg_a:
                pairs.append((a, None))

        elif tag == "insert":
            for b in seg_b:
                pairs.append((None, b))

    return pairs


# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------

def ocr_voting(paddle_results, deepseek_results=None, min_confidence=0.6):
    """
    Ensemble voting between PaddleOCR and DeepSeek OCR line results.

    Args
    ----
    paddle_results   : list[dict] - each dict must have 'text' (str) and
                                    'confidence' (float 0-1).
    deepseek_results : list[dict] | None - same shape; pass None or [] if
                                    DeepSeek was not run or timed out.
    min_confidence   : float - lines below this threshold are discarded
                               (default 0.6).

    Returns
    -------
    list[dict] with keys:
        'text'       - final merged/selected text for this line
        'confidence' - ensemble confidence score
        'source'     - origin tag:
                         'voted(paddle)'   both ran, Paddle confidence led
                         'voted(deepseek)' both ran, DeepSeek confidence led
                         'paddle_only'     only Paddle detected this line
                         'deepseek_only'   only DeepSeek detected this line
                         'paddle'          DeepSeek returned 0 lines / not used
                         'deepseek'        Paddle returned 0 lines
    """

    # Step 0: sanitise and normalise inputs
    paddle_results   = _norm_list(list(paddle_results   or []))
    deepseek_results = _norm_list(list(deepseek_results or []))

    # Step 1: edge cases - one or both engines returned nothing
    if not paddle_results and not deepseek_results:
        return []

    if not paddle_results:
        # Paddle gave 0 lines (crashed/timed out) - fall back to DeepSeek fully
        return [
            {
                "text":       d["text"],
                "confidence": d["confidence"],
                "source":     "deepseek",
            }
            for d in deepseek_results
            if d["confidence"] >= min_confidence
        ]

    if not deepseek_results:
        # DeepSeek gave 0 lines (Ollama offline, timeout) - use Paddle fully
        return [
            {
                "text":       p["text"],
                "confidence": p["confidence"],
                "source":     "paddle",
            }
            for p in paddle_results
            if p["confidence"] >= min_confidence
        ]

    # Step 2: both engines produced results - align lines by content, then vote
    pairs = _align_lines(paddle_results, deepseek_results)
    final_results = []

    for p, d in pairs:

        if p is not None and d is not None:
            # Both engines see this line: word-level vote
            merged_text = _word_level_vote(
                p["text"], p["confidence"],
                d["text"], d["confidence"],
            )
            merged_conf = _weighted_confidence(p["confidence"], d["confidence"])
            source = "paddle" if p["confidence"] >= d["confidence"] else "deepseek"

            if merged_text and merged_conf >= min_confidence:
                final_results.append({
                    "text":       merged_text,
                    "confidence": round(merged_conf, 4),
                    "source":     f"voted({source})",
                })

        elif p is not None:
            # Only Paddle detected this line
            if p["confidence"] >= min_confidence:
                final_results.append({
                    "text":       p["text"],
                    "confidence": p["confidence"],
                    "source":     "paddle_only",
                })

        else:
            # Only DeepSeek detected this line
            if d["confidence"] >= min_confidence:
                final_results.append({
                    "text":       d["text"],
                    "confidence": d["confidence"],
                    "source":     "deepseek_only",
                })

    return final_results
