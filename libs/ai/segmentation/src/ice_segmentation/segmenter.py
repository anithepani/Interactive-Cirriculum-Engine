"""Topic segmentation of a transcript into ordered, titled, summarized segments.

Pipeline:
  a. Extract sentence texts + timestamps from the canonical transcript dict.
  b. Embed each sentence with sentence-transformers (all-MiniLM-L6-v2).
  c. Compute adjacent-sentence cosine similarities; mark boundaries where
     similarity drops below a dynamic threshold (mean - 1*std).
  d. Merge sentences between boundaries into candidate segments (min 2 sentences).
  e. Assign a topic label per segment via BERTopic (falls back to first words).
  f. Call LLMClient.complete() for a 5-word title + 1-sentence summary (JSON).
  g. Extract key concepts via the same LLM (best-effort, non-fatal).
  h. Set structuredness = mean pairwise cosine similarity within the segment.

Returns a list of segment dicts with the exact field set required by the
canonical Segment contract (minus source_frames, which is vision's domain).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from ice_contracts.visual import VisualItem, VisualRegionType

logger = logging.getLogger(__name__)

# ---- Config -------------------------------------------------------------

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_MIN_SENTENCES_PER_SEGMENT = 2
_SIMILARITY_FLOOR = 0.3  # absolute minimum similarity to NOT split
_MAX_CONCEPTS = 5
_MIN_SEGMENT_DURATION_SEC = 15.0  # merge segments shorter than this into prev

# Lazy singletons so the model loads only once per process.
_embedder: SentenceTransformer | None = None
_llm: Any = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(_EMBEDDING_MODEL)
    return _embedder


def _get_llm():
    global _llm
    if _llm is None:
        from ice_llm.client import LLMClient

        _llm = LLMClient()
    return _llm


# ---- Cosine similarity ---------------------------------------------------


def _cosine_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity for a batch of embeddings (N, D) -> (N, N)."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / np.clip(norms, 1e-12, None)
    return normalized @ normalized.T


# ---- Boundary detection (step c) ----------------------------------------


def _find_boundaries(adjacent_sims: np.ndarray, sentences: list[dict], visual_items: list[VisualItem] | None = None) -> list[int]:
    """Return indices (into the sentence list) where a new segment starts.

    A boundary is placed after sentence *i* when the similarity between
    sentence *i* and *i+1* drops below a dynamic threshold, defined as
    `mean - 1*std` of the adjacent similarities, clamped to a floor so
    very coherent text doesn't fragment spuriously.
    If a slide change is detected between sentences, a hard boundary is placed.
    """
    if len(adjacent_sims) < 2:
        return []

    threshold = float(np.mean(adjacent_sims) - np.std(adjacent_sims))
    threshold = max(threshold, _SIMILARITY_FLOOR)

    boundaries: list[int] = []  # sentence index where a new segment begins
    for i, sim in enumerate(adjacent_sims):
        force_boundary = False
        if visual_items:
            # Check for slide changes in this gap
            end_t = sentences[i]["end"]
            start_t = sentences[i+1]["start"]
            for v in visual_items:
                if v.type == VisualRegionType.SLIDE and end_t <= v.ts <= start_t:
                    force_boundary = True
                    break

        if sim < threshold or force_boundary:
            boundaries.append(i + 1)  # new segment starts at i+1
    return boundaries


# ---- Merge into segments (step d) ---------------------------------------


def _merge_into_segments(
    sentences: list[dict], boundaries: list[int]
) -> list[dict]:
    """Group consecutive sentences between boundaries into segment dicts."""
    n = len(sentences)
    # Ensure no boundary violates the min-sentences constraint.
    starts = [0] + boundaries
    starts = [s for s in starts if 0 <= s < n]
    # Deduplicate + sort.
    starts = sorted(set(starts))

    segments: list[dict] = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else n
        if end - start < _MIN_SENTENCES_PER_SEGMENT and segments:
            # Too short — fold into the previous segment.
            segments[-1]["sent_idx_end"] = end
        else:
            segments.append(
                {"sent_idx_start": start, "sent_idx_end": end}
            )
    return segments


def _merge_short_segments(
    segments: list[dict], sentences: list[dict]
) -> list[dict]:
    """Post-processing pass: merge any segment shorter than
    _MIN_SEGMENT_DURATION_SEC into its predecessor.

    Iterates forward so cascaded merges work correctly (a very short segment
    that comes right after another short segment will both be absorbed).
    """
    if not segments:
        return segments

    merged: list[dict] = [segments[0]]
    for seg in segments[1:]:
        lo, hi = seg["sent_idx_start"], seg["sent_idx_end"]
        duration = sentences[hi - 1]["end"] - sentences[lo]["start"]
        if duration < _MIN_SEGMENT_DURATION_SEC:
            # Absorb into previous segment.
            merged[-1]["sent_idx_end"] = hi
            logger.debug(
                "Merged short segment (%.1fs) into predecessor.", duration
            )
        else:
            merged.append(seg)
    return merged


# ---- BERTopic topic labels (step e) -------------------------------------


def _bertopic_labels(texts: list[str]) -> list[str]:
    """Assign a short topic label to each text. Falls back to noun extraction."""
    if len(texts) < 15:
        # BERTopic needs enough docs for UMAP spectral embedding to work
        # (k >= N errors below ~15 docs). Use noun-extraction fallback.
        return [_noun_label(t) for t in texts]
    try:
        from bertopic import BERTopic

        topic_model = BERTopic(
            language="english",
            calculate_probabilities=False,
            verbose=False,
            min_topic_size=2,
        )
        topics, _ = topic_model.fit_transform(texts)
        labels_map: dict[int, str] = {}
        for topic_id in set(topics):
            if topic_id == -1:
                labels_map[topic_id] = "general"
            else:
                raw = topic_model.get_topic_info()
                row = raw[raw["Topic"] == topic_id]
                if not row.empty:
                    words_str = row.iloc[0].get("Name", "")
                    # BERTopic names look like "0_health_character_damage"
                    parts = words_str.split("_", 1)
                    label = parts[1] if len(parts) > 1 else words_str
                    candidate = label.replace("_", " ")[:40]
                    labels_map[topic_id] = candidate
                else:
                    labels_map[topic_id] = "general"
        raw_labels = [labels_map.get(t, "general") for t in topics]
        # Replace any garbage label (mostly stop-words) with noun fallback.
        return [
            _noun_label(texts[i]) if _is_garbage_label(lbl) else lbl
            for i, lbl in enumerate(raw_labels)
        ]
    except Exception as exc:
        logger.warning("BERTopic failed (%s); using noun fallback.", exc)
        return [_noun_label(t) for t in texts]


def _first_words(text: str, n: int = 4) -> str:
    return " ".join(text.split()[:n])


# Stop-words used to detect garbage BERTopic labels.
_LABEL_STOP_WORDS = {
    "we", "the", "to", "and", "a", "an", "of", "in", "is", "are",
    "this", "that", "it", "its", "be", "was", "were", "for", "on",
    "or", "but", "not", "with", "you", "so", "do", "can", "by",
    "have", "has", "had", "will", "just", "our", "them",
}


def _noun_label(text: str, n: int = 3) -> str:
    """Regex fallback: extract the first *n* candidate nouns from *text*.

    A 'noun candidate' is any lower-case token of ≥4 chars that is not a
    stop-word and is not purely numeric.
    """
    tokens = re.findall(r"\b[a-z][a-z0-9_]{3,}\b", text.lower())
    seen: set[str] = set()
    nouns: list[str] = []
    for tok in tokens:
        if tok in _LABEL_STOP_WORDS or tok in seen:
            continue
        seen.add(tok)
        nouns.append(tok)
        if len(nouns) >= n:
            break
    return " ".join(nouns) if nouns else _first_words(text)


def _is_garbage_label(label: str) -> bool:
    """Return True when *label* is mostly stop-words (BERTopic noise)."""
    tokens = label.lower().split()
    if not tokens:
        return True
    stop_ratio = sum(1 for t in tokens if t in _LABEL_STOP_WORDS) / len(tokens)
    return stop_ratio > 0.5


# ---- LLM title + summary (step f) ---------------------------------------


def _extract_json(raw: str) -> dict | None:
    """Parse a JSON object from an LLM string, tolerating markdown fences."""
    # Strip ```json ... ``` or ``` ... ``` fences.
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    # Find the first {...} block.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _llm_title_summary(text: str) -> tuple[str, str]:
    """Ask the LLM for a 5-word title + 1-sentence summary; parse the JSON."""
    prompt = (
        f"Given this text segment from a technical tutorial: {text}. "
        "Write a short 5-word title and a 1-sentence summary of what this "
        "segment teaches. Return a JSON with 'title' and 'summary'."
    )
    raw = _get_llm().complete(prompt, tier="high_value")
    parsed = _extract_json(raw)
    if parsed and "title" in parsed and "summary" in parsed:
        return str(parsed["title"]), str(parsed["summary"])
    # Fallback: if the LLM didn't return valid JSON, use the raw text.
    return _first_words(text, 5), raw.strip().split("\n")[0][:120]


# ---- Key concepts (step g) ----------------------------------------------


def _llm_extract_concepts(text: str) -> list[str]:
    """Ask the LLM for key concepts; non-fatal on error."""
    prompt = (
        f"Extract up to {_MAX_CONCEPTS} key technical concepts from this "
        f"tutorial segment. Return a JSON array of strings, e.g. "
        f'["class", "__init__"]. Text: {text}'
    )
    try:
        raw = _get_llm().complete(prompt, tier="bulk")
        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            # LLM might wrap in {"concepts": [...]}
            for key in ("concepts", "items", "list"):
                if key in parsed and isinstance(parsed[key], list):
                    return [str(c) for c in parsed[key]][:_MAX_CONCEPTS]
        if isinstance(parsed, list):
            return [str(c) for c in parsed][:_MAX_CONCEPTS]
        return _keyword_concepts(text)
    except Exception as exc:
        logger.warning("Concept extraction failed (%s); using keywords.", exc)
        return _keyword_concepts(text)


def _keyword_concepts(text: str) -> list[str]:
    """Cheap fallback: extract capitalized/code-like tokens."""
    tokens = re.findall(r"\b[a-z_][a-z0-9_]*\b", text)
    stop = {
        "the", "a", "an", "is", "are", "to", "in", "of", "and", "or", "for",
        "we", "can", "this", "that", "with", "like", "its", "our", "let",
        "now", "also", "when", "which", "from", "not", "but", "by", "on",
        "it", "be", "has", "have", "was", "were", "so", "here", "some",
    }
    seen: set[str] = set()
    result: list[str] = []
    for t in tokens:
        if t in stop or len(t) < 3 or t in seen:
            continue
        seen.add(t)
        result.append(t)
        if len(result) >= _MAX_CONCEPTS:
            break
    return result


# ---- Structuredness (step h) --------------------------------------------


def _structuredness(embeddings: np.ndarray) -> float:
    """Mean pairwise cosine similarity within a segment, clamped to [0, 1]."""
    if len(embeddings) < 2:
        return 1.0
    sim = _cosine_similarity_matrix(embeddings)
    # Upper triangle (excluding diagonal) — pairwise only.
    iu = np.triu_indices(len(embeddings), k=1)
    return float(np.clip(np.mean(sim[iu]), 0.0, 1.0))


# ---- Main entry point ---------------------------------------------------


def segment_transcript(transcript_dict: dict, visual_items: list[VisualItem] | None = None) -> list[dict]:
    """Segment a canonical transcript dict into ordered topic segments.

    Args:
        transcript_dict: the canonical transcript JSON produced by
            ``ice_transcript.transcribe()`` — must contain ``segments``
            with ``text``, ``start``, ``end``, and ``words``.
        visual_items: Optional extracted visual elements (M3).

    Returns:
        A list of segment dicts, each with keys: ``id`` (int, sequential),
        ``start`` (float), ``end`` (float), ``title`` (str), ``summary``
        (str), ``concepts`` (list[str]), ``structuredness`` (float 0-1),
        ``source_frames`` (list[int]).
    """
    raw_segments = transcript_dict.get("segments", [])
    if not raw_segments:
        return []

    # (a) Extract sentence texts + timestamps.
    sentences: list[dict] = []
    for seg in raw_segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        sentences.append(
            {
                "text": text,
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
            }
        )
    if not sentences:
        return []

    texts = [s["text"] for s in sentences]

    # (b) Embed each sentence.
    embedder = _get_embedder()
    embeddings = embedder.encode(
        texts, convert_to_numpy=True, show_progress_bar=False
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    # (c) Adjacent-sentence cosine similarities + boundary detection.
    if len(embeddings) >= 2:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normed = embeddings / np.clip(norms, 1e-12, None)
        adjacent_sims = np.array(
            [float(np.dot(normed[i], normed[i + 1]))
             for i in range(len(normed) - 1)]
        )
        boundaries = _find_boundaries(adjacent_sims, sentences, visual_items)
    else:
        boundaries = []

    # (d) Merge into candidate segments.
    candidate_segments = _merge_into_segments(sentences, boundaries)
    if not candidate_segments:
        candidate_segments = [
            {"sent_idx_start": 0, "sent_idx_end": len(sentences)}
        ]

    # (d-post) Merge segments shorter than _MIN_SEGMENT_DURATION_SEC into prev.
    candidate_segments = _merge_short_segments(candidate_segments, sentences)

    # (e) BERTopic topic labels.
    segment_texts = [
        " ".join(texts[c["sent_idx_start"]: c["sent_idx_end"]])
        for c in candidate_segments
    ]
    topic_labels = _bertopic_labels(segment_texts)

    # (f)(g)(h) Per-segment: LLM title/summary, concepts, structuredness.
    results: list[dict] = []
    for idx, cand in enumerate(candidate_segments):
        lo, hi = cand["sent_idx_start"], cand["sent_idx_end"]
        seg_sentences = sentences[lo:hi]
        seg_text = segment_texts[idx]
        seg_embeddings = embeddings[lo:hi]

        start = seg_sentences[0]["start"]
        end = seg_sentences[-1]["end"]

        # Fuse visual items
        seg_source_frames = []
        nudge = 0.0
        if visual_items:
            for v in visual_items:
                if start <= v.ts <= end:
                    seg_source_frames.append(v.frame_idx)
                    if v.type == VisualRegionType.CODE and v.text.strip():
                        seg_text += f"\n\n[Code Block]:\n{v.text}"
                    elif v.type in (VisualRegionType.DIAGRAM, VisualRegionType.UI):
                        nudge += 0.1

            seg_source_frames = sorted(list(set(seg_source_frames)))

        title, summary = _llm_title_summary(seg_text)
        concepts = _llm_extract_concepts(seg_text)
        
        base_struct = _structuredness(seg_embeddings)
        structuredness = min(1.0, base_struct + nudge)

        results.append(
            {
                "id": idx + 1,
                "start": start,
                "end": end,
                "title": title,
                "summary": summary,
                "concepts": concepts,
                "structuredness": round(structuredness, 4),
                "topic_label": topic_labels[idx],
                "source_frames": seg_source_frames,
            }
        )

    return results
