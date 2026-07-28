"""YouTube caption harvesting (Block F).

Before falling back to Whisper ASR, try to reuse the video's *existing*
subtitles. Manual (human) captions are preferred over auto-generated ones, and
languages are tried in the configured priority order
(``settings.pipeline.caption_langs``).

If captions are found they are downloaded via yt-dlp (WebVTT format), parsed
into the canonical transcript contract that ``ice_transcript.transcribe()``
emits, and returned so the pipeline can skip ASR entirely. When no usable
captions exist we return ``None`` and the caller runs Whisper as before.

Canonical transcript contract (matches ice_transcript.transcribe):
    {"language": str, "confidence": float, "source": "captions",
     "segments": [{"id": int, "start": float, "end": float, "text": str,
                   "speaker": "SPEAKER_00", "words": [], "confidence": float}]}
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Any, Optional

import yt_dlp
from ice_shared.settings import settings

logger = logging.getLogger(__name__)

SPEAKER_LABEL = "SPEAKER_00"

# WebVTT timestamp: HH:MM:SS.mmm or MM:SS.mmm  ->  seconds.
_TS_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?")
# A cue time line: "00:00:01.000 --> 00:00:04.000 [align:...]"
_CUE_RE = re.compile(
    r"(\d{1,2}:\d{1,2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*"
    r"(\d{1,2}:\d{1,2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})"
)
# Inline tags YouTube embeds in auto-captions: <00:00:01.000><c> word</c>
_TAG_RE = re.compile(r"<[^>]+>")


def _ts_to_seconds(ts: str) -> float:
    """Parse a WebVTT/SRT timestamp string into float seconds."""
    m = _TS_RE.search(ts.strip())
    if not m:
        return 0.0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    millis = int((m.group(4) or "0").ljust(3, "0")[:3])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def _clean_text(raw: str) -> str:
    """Strip inline VTT tags and collapse whitespace."""
    txt = _TAG_RE.sub("", raw)
    txt = txt.replace("&nbsp;", " ")
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def _parse_vtt(vtt: str) -> list[dict]:
    """Parse WebVTT text into de-duplicated {start,end,text} cues.

    YouTube auto-captions repeat rolling lines across consecutive cues; we drop
    a cue whose text is empty or identical to the previously kept line so the
    transcript reads cleanly.
    """
    cues: list[dict] = []
    blocks = re.split(r"\n\s*\n", vtt.replace("\r\n", "\n").replace("\r", "\n"))
    last_text = ""
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        cue_line = next((ln for ln in lines if "-->" in ln), None)
        if not cue_line:
            continue
        m = _CUE_RE.search(cue_line)
        if not m:
            continue
        start = _ts_to_seconds(m.group(1))
        end = _ts_to_seconds(m.group(2))
        text_lines = lines[lines.index(cue_line) + 1 :]
        text = _clean_text(" ".join(text_lines))
        if not text or text == last_text:
            continue
        # Skip WebVTT header noise.
        if text.upper().startswith(("WEBVTT", "KIND:", "LANGUAGE:")):
            continue
        cues.append({"start": start, "end": end, "text": text})
        last_text = text
    return cues


def _pick_language(available: dict[str, Any], langs: list[str]) -> Optional[str]:
    """Return the first configured language present in *available*, else None."""
    if not available:
        return None
    for want in langs:
        if want in available:
            return want
    # Loose match: e.g. want "en" matches "en-US".
    for want in langs:
        for have in available:
            if have.split("-")[0] == want.split("-")[0]:
                return have
    return None


def _probe_subtitles(url: str) -> tuple[dict, dict]:
    """Return (manual_subs, automatic_subs) dicts keyed by language code."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
    }
    if os.path.exists("/app/cookies.txt"):
        opts["cookiefile"] = "/app/cookies.txt"
    else:
        opts["extractor_args"] = {"youtube": ["player_client=android"]}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False) or {}
    return (info.get("subtitles") or {}, info.get("automatic_captions") or {})


def _download_vtt(url: str, lang: str, automatic: bool, out_dir: str) -> Optional[str]:
    """Download the chosen subtitle track as WebVTT; return its file path."""
    outtmpl = os.path.join(out_dir, "caption.%(ext)s")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": [lang],
        "writesubtitles": not automatic,
        "writeautomaticsub": automatic,
        "outtmpl": outtmpl,
    }
    if os.path.exists("/app/cookies.txt"):
        opts["cookiefile"] = "/app/cookies.txt"
    else:
        opts["extractor_args"] = {"youtube": ["player_client=android"]}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    for fname in os.listdir(out_dir):
        if fname.startswith("caption.") and fname.endswith(".vtt"):
            return os.path.join(out_dir, fname)
    return None


def harvest_captions(url: str) -> Optional[dict]:
    """Try to build a transcript from existing YouTube captions.

    Returns the canonical transcript dict on success, or ``None`` when caption
    harvesting is disabled, unavailable, or fails — signalling the caller to run
    Whisper ASR. Never raises: any error degrades gracefully to ``None``.
    """
    if not settings.pipeline.prefer_captions:
        return None

    langs = [c.strip() for c in settings.pipeline.caption_langs.split(",") if c.strip()]
    if not langs:
        langs = ["en"]

    try:
        manual, automatic = _probe_subtitles(url)
    except Exception as e:  # network / private / no captions
        logger.info("caption probe failed (%s); will use ASR", e)
        return None

    # Prefer manual (human) captions over auto-generated.
    lang = _pick_language(manual, langs)
    is_auto = False
    if lang is None:
        lang = _pick_language(automatic, langs)
        is_auto = True
    if lang is None:
        logger.info("no captions in %s; will use ASR", langs)
        return None

    try:
        with tempfile.TemporaryDirectory(prefix="ice_caps_") as tmp:
            vtt_path = _download_vtt(url, lang, is_auto, tmp)
            if not vtt_path or not os.path.exists(vtt_path):
                logger.info("caption download produced no file; will use ASR")
                return None
            with open(vtt_path, encoding="utf-8", errors="replace") as fh:
                cues = _parse_vtt(fh.read())
    except Exception as e:
        logger.info("caption download/parse failed (%s); will use ASR", e)
        return None

    if not cues:
        logger.info("parsed 0 caption cues; will use ASR")
        return None

    segments = [
        {
            "id": idx,
            "start": float(c["start"]),
            "end": float(c["end"]),
            "text": c["text"],
            "speaker": SPEAKER_LABEL,
            "words": [],
            "confidence": 1.0,
        }
        for idx, c in enumerate(cues)
    ]
    logger.info(
        "harvested %d caption cues (lang=%s, %s) — skipping ASR",
        len(segments),
        lang,
        "auto" if is_auto else "manual",
    )
    return {
        "language": lang.split("-")[0],
        "confidence": 1.0,
        "source": "captions",
        "segments": segments,
    }


__all__ = ["harvest_captions"]
