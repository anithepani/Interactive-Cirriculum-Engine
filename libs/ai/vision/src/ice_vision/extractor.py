"""M3 Vision module: extracts frames, runs OCR, classifies regions, and parses code."""
from __future__ import annotations

import logging
import os
import threading
import urllib.request
import tempfile
from collections import Counter
import cv2
import numpy as np
from PIL import Image

# Import settings for device fallback
from ice_shared.settings import settings
from ice_contracts.visual import VisualItem, VisualRegionType

logger = logging.getLogger(__name__)

_ocr_engine = None
_ocr_engine_lock = threading.Lock()
_trocr_model = None
_trocr_processor = None
_ts_parser = None


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        with _ocr_engine_lock:
            if _ocr_engine is None:
                # Cap ONNX intra-op threads so the threaded OCR pool (each worker
                # shares this one engine) doesn't oversubscribe cores. ONNX
                # Runtime reads OMP_NUM_THREADS when it initializes its thread
                # pool, so this must happen before rapidocr/onnxruntime is
                # imported. setdefault never overrides an operator-provided
                # value.
                intra = settings.vision.onnx_intra_op_threads
                if intra > 0:
                    os.environ.setdefault("OMP_NUM_THREADS", str(intra))
                from rapidocr_onnxruntime import RapidOCR

                _ocr_engine = RapidOCR()
    return _ocr_engine


def _get_trocr(device: str = "cpu"):
    global _trocr_model, _trocr_processor
    if not settings.vision.enable_heavy_fallbacks:
        raise RuntimeError("TrOCR is disabled. Set VISION_ENABLE_HEAVY_FALLBACKS=true to enable.")
    if _trocr_model is None:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-small-printed")
        _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-printed")
        _trocr_model.to(device)
    return _trocr_processor, _trocr_model


def _get_ts_parser():
    global _ts_parser
    if _ts_parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_python as tspython

        _ts_parser = Parser(Language(tspython.language()))
    return _ts_parser


def _download_espcn() -> str:
    """Download the ESPCN_x2 model if not present."""
    model_path = os.path.join(tempfile.gettempdir(), "ESPCN_x2.pb")
    if not os.path.exists(model_path):
        url = "https://github.com/fannymonori/TF-ESPCN/raw/master/export/ESPCN_x2.pb"
        try:
            urllib.request.urlretrieve(url, model_path)
        except Exception as e:
            logger.warning(f"Failed to download ESPCN model: {e}")
            return ""
    return model_path


def _upscale_image(img: np.ndarray) -> np.ndarray | None:
    try:
        model_path = _download_espcn()
        if not model_path:
            return None
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(model_path)
        sr.setModel("espcn", 2)
        return sr.upsample(img)
    except Exception as e:
        logger.warning(f"Upscaling failed: {e}")
        return None


def _extract_frames(
    video_path: str,
    extract_rate_sec: float,
    dedup_threshold: float = 0.08,
    max_frames: int = 150
) -> list[tuple[int, float, np.ndarray]]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_interval = max(1, int(fps * extract_rate_sec))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dedup_limit = 64 * 64 * dedup_threshold

    kept: list[tuple[int, float, np.ndarray]] = []
    # Compare each candidate against a short window of recently-kept frames so
    # recurring near-duplicates (e.g. a held slide) are dropped cheaply, not only
    # when they happen to follow the immediately-previous kept frame.
    recent_hashes: list[np.ndarray] = []
    dedup_window = 3

    def _consider(frame: np.ndarray, idx: int) -> bool:
        small = cv2.resize(frame, (64, 64))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        curr_hash = gray > gray.mean()
        for ph in recent_hashes:
            if np.count_nonzero(curr_hash != ph) < dedup_limit:
                return False
        kept.append((len(kept), idx / fps, frame))
        recent_hashes.append(curr_hash)
        if len(recent_hashes) > dedup_window:
            recent_hashes.pop(0)
        return True

    # Primary path: seek to each sample index and decode only that frame. This
    # avoids decoding every frame of a long video (the big latency win for a
    # 10-min screen recording — ~1 decode per sample instead of thousands).
    sample_idx = 0
    seek_broken = False
    while len(kept) < max_frames:
        if total_frames > 0 and sample_idx >= total_frames:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_idx)
        ret, frame = cap.read()
        if not ret:
            if not kept:
                seek_broken = True
            break
        _consider(frame, sample_idx)
        sample_idx += frame_interval

    # Fallback: some containers/codecs can't seek accurately and return no
    # frames. Use a cheap grab()-based pass that advances without decoding to
    # numpy and only decodes (read()) at sample points — still far cheaper than
    # decoding every frame.
    if seek_broken:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_idx = 0
        while len(kept) < max_frames:
            if frame_idx % frame_interval == 0:
                ret, frame = cap.read()
                if not ret:
                    break
                _consider(frame, frame_idx)
            else:
                if not cap.grab():
                    break
            frame_idx += 1

    if len(kept) >= max_frames:
        logger.warning(f"Reached maximum frame limit of {max_frames}. Stopping frame extraction.")

    cap.release()
    return kept


# IDE / terminal chrome that OCR picks up from a screen recording but which is
# NOT lesson code. If a frame is dominated by these, it's an editor screenshot
# (file tree, menus, run output), not a code snippet worth surfacing (Issue 2).
_IDE_METADATA_MARKERS = (
    "main.py", "builtins", "structure", "run:", "run ", "terminal",
    "console", "output", "explorer", "project", "navigate", "refactor",
    "problems", "version control", "search everywhere", "process finished",
    "exit code", ".idea", "__pycache__", "site-packages", "external libraries",
)

# Signals that a line is genuinely a line of code (not prose / a menu label).
_CODE_TOKEN_KEYWORDS = {
    "def", "class", "import", "return", "from", "public", "void",
    "for", "while", "if", "elif", "else", "print", "lambda", "yield",
    "async", "await", "try", "except", "with",
}


def _looks_like_code_line(line: str) -> bool:
    """True when a single line has the shape of source code, not prose/UI text."""
    s = line.strip()
    if not s:
        return False
    words = set(s.lower().replace("(", " ").replace(":", " ").split())
    if words & _CODE_TOKEN_KEYWORDS:
        return True
    # Structural signals: indented assignment/call, block-open, call syntax.
    if line[:1] in (" ", "\t") and any(c in s for c in "=(:"):
        return True
    if s.endswith(":"):
        return True
    if "()" in s or ("(" in s and ")" in s and "=" in s):
        return True
    return False


def _metadata_ratio(text: str) -> float:
    """Fraction of non-empty lines that read as IDE/terminal chrome, not code."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 1.0
    hits = sum(
        1 for ln in lines if any(m in ln.lower() for m in _IDE_METADATA_MARKERS)
    )
    return hits / len(lines)


def _classify_region(text: str, img_shape: tuple[int, ...]) -> VisualRegionType:
    text_lower = text.lower()

    # An editor/terminal screenshot is dominated by IDE chrome — treat it as a
    # SLIDE so its noisy OCR never becomes an exercise code snippet (Issue 2).
    if _metadata_ratio(text) >= 0.4:
        return VisualRegionType.SLIDE

    # Require MULTIPLE code-shaped lines before calling a frame CODE. A single
    # stray keyword (e.g. "import" in a menu label) is not enough — that
    # false-positive pulled whole IDE frames in as "code".
    code_lines = sum(1 for ln in text.splitlines() if _looks_like_code_line(ln))
    if code_lines >= 2:
        return VisualRegionType.CODE

    if "architecture" in text_lower or "flow" in text_lower or "diagram" in text_lower:
        return VisualRegionType.DIAGRAM

    return VisualRegionType.SLIDE


def _sanitize_code(text: str) -> str:
    """Keep only code-shaped lines, dropping interleaved IDE/terminal chrome.

    OCR of an editor frame mixes real code with menu labels, the file tree, and
    terminal output. We drop lines that read as IDE metadata or don't look like
    code; if stripping leaves nothing useful we fall back to the original text
    so a genuine snippet is never lost.
    """
    kept: list[str] = []
    for ln in text.splitlines():
        low = ln.lower()
        if any(m in low for m in _IDE_METADATA_MARKERS):
            continue
        # Keep code-shaped lines, plus continuation lines once code has started.
        if _looks_like_code_line(ln) or (ln.strip() and kept):
            kept.append(ln)
    cleaned = "\n".join(kept).strip()
    if not cleaned:
        return text.strip()
    # Best-effort parse (validation only; we keep the cleaned text regardless).
    try:
        parser = _get_ts_parser()
        parser.parse(bytes(cleaned, "utf8"))
    except Exception:
        pass
    return cleaned


def _ocr_single_frame(args: tuple) -> dict | None:
    f_idx, ts, frame, device = args
    try:
        # Downscale wide frames before OCR. Large screen recordings OCR much
        # faster at <= ocr_max_width px with negligible accuracy loss for
        # slide/code text. Bbox is normalized later, so scaling is safe.
        max_width = settings.vision.ocr_max_width
        if max_width and frame.shape[1] > max_width:
            h0, w0 = frame.shape[:2]
            frame = cv2.resize(
                frame, (max_width, int(h0 * (max_width / w0))),
                interpolation=cv2.INTER_AREA,
            )
        # Convert BGR to RGB for OCR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ocr = _get_ocr_engine()
        result, _ = ocr(rgb_frame)
        
        if not result:
            return None
            
        total_conf = 0.0
        texts = []
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = 0.0, 0.0
        
        h, w = frame.shape[:2]
        
        for line in result:
            box, text, conf = line
            texts.append(text)
            total_conf += conf
            
            for pt in box:
                min_x = min(min_x, pt[0])
                min_y = min(min_y, pt[1])
                max_x = max(max_x, pt[0])
                max_y = max(max_y, pt[1])
                
        avg_conf = total_conf / len(result)
        full_text = "\n".join(texts)
        
        # Confidence threshold check
        if avg_conf < settings.vision.ocr_confidence_threshold:
            if settings.vision.enable_heavy_fallbacks:
                # Try Upscaling
                logger.debug(f"Low confidence ({avg_conf:.2f}) on frame {f_idx}, attempting upscale...")
                upscaled = _upscale_image(frame)
                if upscaled is not None:
                    upscaled_rgb = cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB)
                    up_result, _ = ocr(upscaled_rgb)
                    if up_result:
                        up_texts = []
                        up_conf = 0.0
                        for line in up_result:
                            up_texts.append(line[1])
                            up_conf += line[2]
                        up_avg_conf = up_conf / len(up_result)
                        if up_avg_conf > avg_conf:
                            full_text = "\n".join(up_texts)
                            avg_conf = up_avg_conf
                
                # If still low, use TrOCR
                if avg_conf < settings.vision.ocr_confidence_threshold:
                    try:
                        processor, model = _get_trocr(device)
                        pil_img = Image.fromarray(rgb_frame)
                        pixel_values = processor(pil_img, return_tensors="pt").pixel_values.to(device)
                        generated_ids = model.generate(pixel_values)
                        trocr_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                        if len(trocr_text.strip()) > 0:
                            full_text = trocr_text
                            avg_conf = 0.85
                    except Exception as e:
                        logger.warning(f"TrOCR fallback failed: {e}")
            else:
                # Discard frames with no readable text when fallbacks are disabled
                if not full_text.strip():
                    return None

        region_type = _classify_region(full_text, frame.shape)
        
        if region_type == VisualRegionType.CODE:
            full_text = _sanitize_code(full_text)
            
        # Normalize bbox
        bbox = [
            min_x / w,
            min_y / h,
            (max_x - min_x) / w,
            (max_y - min_y) / h
        ]
        
        return {
            "frame_idx": f_idx,
            "ts": ts,
            "type": region_type,
            "text": full_text,
            "bbox": bbox,
            "confidence": avg_conf,
            "code_lang": "python" if region_type == VisualRegionType.CODE else None
        }
    except Exception as e:
        logger.error(f"Error processing frame {f_idx} at {ts}s: {e}")
        return None


def extract_visuals(
    video_path: str,
    extract_rate_sec: float | None = None,
    device: str | None = None
) -> list[VisualItem]:
    """
    Extract keyframes from a video, run OCR, classify regions, and sanitize code.
    
    Args:
        video_path: Path to the video file.
        extract_rate_sec: How often to extract a frame (in seconds).
        device: "cpu" or "cuda" (defaults to settings or "cpu").
        
    Returns:
        List of VisualItem objects adhering to the contract.
    """
    if device is None:
        device = os.environ.get("OCR_DEVICE", "cpu")
    if extract_rate_sec is None:
        extract_rate_sec = settings.vision.extract_rate_sec
        
    logger.info(f"Extracting visuals from {video_path} at {extract_rate_sec}s intervals (device={device})")
    
    try:
        frames = _extract_frames(
            video_path,
            extract_rate_sec,
            dedup_threshold=settings.vision.dedup_threshold,
            max_frames=settings.vision.max_frames
        )
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
        return []

    if not frames:
        return []

    # Parallel processing of frames via ThreadPoolExecutor
    max_workers = settings.vision.max_workers
    if max_workers <= 0:
        max_workers = min(os.cpu_count() or 1, 4)

    # Arguments to pass to the pool. With threads (not processes) the frames
    # stay in shared memory — no pickling of large BGR arrays across processes.
    tasks = [(f_idx, ts, frame, device) for f_idx, ts, frame in frames]
    visual_items = []

    if max_workers == 1:
        logger.info("Running OCR sequentially (max_workers=1)")
        for task in tasks:
            res = _ocr_single_frame(task)
            if res is not None:
                item = VisualItem(
                    frame_idx=res["frame_idx"],
                    ts=res["ts"],
                    type=res["type"],
                    text=res["text"],
                    bbox=res["bbox"],
                    confidence=res["confidence"],
                    code_lang=res["code_lang"]
                )
                visual_items.append(item)
    else:
        logger.info(f"Running OCR on {len(frames)} frames with {max_workers} threads")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        try:
            # Threads (not processes): RapidOCR / ONNX Runtime releases the GIL
            # during inference, giving real parallelism while avoiding the
            # "daemonic processes are not allowed to have children" crash that
            # happens when a ProcessPoolExecutor is created inside Celery's
            # preforked daemon worker. The module-global OCR engine stays warm
            # (no per-worker cold start).
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_ocr_single_frame, task) for task in tasks]
                for future in as_completed(futures):
                    res = future.result()
                    if res is not None:
                        item = VisualItem(
                            frame_idx=res["frame_idx"],
                            ts=res["ts"],
                            type=res["type"],
                            text=res["text"],
                            bbox=res["bbox"],
                            confidence=res["confidence"],
                            code_lang=res["code_lang"]
                        )
                        visual_items.append(item)
        except Exception as e:
            logger.error(f"Threaded OCR execution failed: {e}. Falling back to sequential execution.")
            visual_items = []
            for task in tasks:
                res = _ocr_single_frame(task)
                if res is not None:
                    item = VisualItem(
                        frame_idx=res["frame_idx"],
                        ts=res["ts"],
                        type=res["type"],
                        text=res["text"],
                        bbox=res["bbox"],
                        confidence=res["confidence"],
                        code_lang=res["code_lang"]
                    )
                    visual_items.append(item)

    # Sort items by frame index
    visual_items.sort(key=lambda x: x.frame_idx)
    logger.info(f"Extracted {len(visual_items)} visual items")
    return visual_items
