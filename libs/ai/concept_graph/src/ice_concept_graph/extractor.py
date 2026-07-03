"""M5 Knowledge Graph / Concept Mapper - concept node + edge extraction.

Builds a concept graph from M4 segments: deduplicates concepts across segments,
enriches them with LLM-generated descriptions + difficulty ratings, then extracts
prerequisite/related/part_of edges between concept pairs via a single batched LLM call.

Lead: Aryan. Support: Zubair (storage).
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# Stop-words leaked by M4's keyword-fallback concept extractor.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "in", "of", "and", "or", "for",
    "we", "can", "this", "that", "with", "like", "its", "our", "let",
    "now", "also", "when", "which", "from", "not", "but", "by", "on",
    "it", "be", "has", "have", "was", "were", "so", "here", "some",
    "you", "see", "say", "want", "just", "take", "first", "two", "down",
    "add", "added", "called", "always", "first", "being", "supplied",
}

_MAX_CONCEPTS = 30


def _slugify(label: str) -> str:
    """Convert a concept label to a stable dot-separated id.

    e.g. "Python classes" -> "python.classes", "__init__ method" -> "init.method"
    """
    cleaned = re.sub(r"[^a-z0-9 ]+", "", label.lower()).strip()
    if not cleaned:
        cleaned = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
    parts = [p for p in cleaned.split() if p]
    return ".".join(parts) if parts else "concept"


def _filter_concepts(raw_concepts: list[str]) -> list[str]:
    """Deduplicate + filter stop-words + cap the total count."""
    seen: set[str] = set()
    result: list[str] = []
    for c in raw_concepts:
        c = c.strip()
        if not c or len(c) < 3:
            continue
        key = c.lower()
        if key in _STOPWORDS or key in seen:
            continue
        seen.add(key)
        result.append(c)
        if len(result) >= _MAX_CONCEPTS:
            break
    return result


def _extract_json(raw: str) -> dict | list | None:
    """Parse JSON from an LLM string, tolerating markdown fences + prose.

    Tries multiple non-greedy matches since the LLM may emit several JSON
    blocks separated by prose (e.g. a draft array + a corrected array).
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    # Try direct parse first.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try each non-greedy [...] and {...} match in order.
    for pattern in (r"\[.*?\]", r"\{.*?\}"):
        for match in re.finditer(pattern, cleaned, re.DOTALL):
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    return None


# ---- Node enrichment (1 LLM call) ---------------------------------------


def _enrich_nodes(concepts: list[str], llm) -> list[dict]:
    """Ask the LLM to generate descriptions + difficulty for all concepts at once."""
    concept_list = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(concepts))
    prompt = (
        "For each of the following programming/tutorial concepts, write a short "
        "1-sentence description and assign a difficulty rating from 1 (beginner) "
        "to 5 (advanced). Return a JSON array where each element has fields: "
        '"label" (the original concept), "description" (str), "difficulty" (int 1-5).\n\n'
        f"Concepts:\n{concept_list}"
    )
    raw = llm.complete(prompt, tier="high_value")
    parsed = _extract_json(raw)
    if not isinstance(parsed, list):
        logger.warning("Node enrichment LLM returned non-list; using defaults.")
        return [
            {
                "id": _slugify(c),
                "label": c,
                "description": c,
                "difficulty": 3,
            }
            for c in concepts
        ]

    # Map by label (case-insensitive) to survive LLM rewording.
    label_map: dict[str, dict] = {}
    for item in parsed:
        if isinstance(item, dict) and "label" in item:
            label_map[str(item["label"]).strip().lower()] = item

    nodes: list[dict] = []
    for c in concepts:
        item = label_map.get(c.lower(), {})
        desc = str(item.get("description", c)).strip() or c
        diff = item.get("difficulty", 3)
        try:
            diff = max(1, min(5, int(diff)))
        except (ValueError, TypeError):
            diff = 3
        nodes.append(
            {
                "id": _slugify(c),
                "label": c,
                "description": desc,
                "difficulty": diff,
            }
        )
    return nodes


# ---- Edge extraction (1 batched LLM call) --------------------------------


def _extract_edges(nodes: list[dict], llm) -> list[dict]:
    """Ask the LLM to classify all concept pairs in a single call."""
    if len(nodes) < 2:
        return []
    concept_lines = "\n".join(
        f"  - id=\"{n['id']}\", label=\"{n['label']}\", description=\"{n['description']}\""
        for n in nodes
    )
    prompt = (
        "Below is a list of concepts extracted from a technical tutorial. "
        "For every meaningful pair, determine the relationship. Return a JSON "
        'array of objects with fields: "src_concept_id" (string), '
        '"dst_concept_id" (string), "relation" (one of "prerequisite", '
        '"related", "part_of"). Only include pairs with a real relationship. '
        "IMPORTANT: use the exact string id values shown below (e.g. "
        '"classes", "self") for src_concept_id and dst_concept_id. '
        "Do NOT use numbers or index positions.\n\n"
        "Direction for 'prerequisite': src is a prerequisite FOR dst (must be "
        "learned before dst). For 'part_of': src is a part OF dst.\n\n"
        f"Concepts:\n{concept_lines}\n\n"
        "Return ONLY the JSON array, no other text."
    )
    raw = llm.complete(prompt, tier="high_value")
    parsed = _extract_json(raw)

    if not isinstance(parsed, list):
        logger.warning("Edge extraction LLM returned non-list; no edges.")
        return []

    valid_ids = {n["id"] for n in nodes}
    valid_relations = {"prerequisite", "related", "part_of"}
    edges: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in parsed:
        if not isinstance(item, dict):
            continue
        src = str(item.get("src_concept_id", "")).strip()
        dst = str(item.get("dst_concept_id", "")).strip()
        relation = str(item.get("relation", "none")).strip().lower()
        if relation not in valid_relations:
            continue
        if src not in valid_ids or dst not in valid_ids or src == dst:
            continue
        key = (src, dst, relation)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "src_concept_id": src,
                "dst_concept_id": dst,
                "relation": relation,
            }
        )
    return edges


# ---- Main entry point ----------------------------------------------------


def extract_concepts_and_edges(segments: list[dict]) -> dict:
    """Build a concept graph from M4 segments.

    Args:
        segments: list of M4 segment dicts, each containing a ``concepts``
            field (list[str]) produced by the segmenter.

    Returns:
        A dict with keys ``concepts`` (list of node dicts with id, label,
        description, difficulty) and ``edges`` (list of edge dicts with
        src_concept_id, dst_concept_id, relation).
    """
    from ice_llm.client import LLMClient

    # Collect + deduplicate concepts across all segments.
    raw_concepts: list[str] = []
    for seg in segments:
        raw_concepts.extend(seg.get("concepts", []))
    concepts = _filter_concepts(raw_concepts)

    if not concepts:
        return {"concepts": [], "edges": []}

    llm = LLMClient()

    # Step 1: enrich nodes (1 LLM call).
    nodes = _enrich_nodes(concepts, llm)

    # Step 2: extract edges (1 LLM call).
    edges = _extract_edges(nodes, llm)

    return {"concepts": nodes, "edges": edges}
