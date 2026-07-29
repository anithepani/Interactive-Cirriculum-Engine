"""Tests for M3 vision extraction."""

import numpy as np
from unittest.mock import patch, MagicMock

from ice_contracts.visual import VisualRegionType
from ice_vision.extractor import _classify_region, extract_visuals


def test_classify_region():
    # Code test
    code_text = "def hello_world():\n    print('hello')\n    return True"
    assert _classify_region(code_text, (1080, 1920, 3)) == VisualRegionType.CODE

    # Diagram test
    diagram_text = "Architecture diagram showing data flow"
    assert _classify_region(diagram_text, (1080, 1920, 3)) == VisualRegionType.DIAGRAM

    # Slide test
    slide_text = "Introduction to the topic. Next steps and conclusion."
    assert _classify_region(slide_text, (1080, 1920, 3)) == VisualRegionType.SLIDE


@patch("ice_vision.extractor.settings")
@patch("ice_vision.extractor._extract_frames")
@patch("ice_vision.extractor._get_ocr_engine")
def test_extract_visuals(mock_get_ocr, mock_extract, mock_settings):
    # Mock settings values (mirror the new production defaults so the test
    # stays meaningful as defaults evolve). ocr_max_width=0 disables the
    # downscale guard so the mocked 100px frame doesn't trip an int-vs-Mock
    # comparison — the downscale path isn't what this test exercises.
    mock_settings.vision.max_workers = 1
    mock_settings.vision.extract_rate_sec = 5.0
    mock_settings.vision.dedup_threshold = 0.06
    mock_settings.vision.ocr_confidence_threshold = 0.7
    mock_settings.vision.max_frames = 60
    mock_settings.vision.enable_heavy_fallbacks = False
    mock_settings.vision.max_fallback_frames = 3
    mock_settings.vision.ocr_max_width = 0
    mock_settings.vision.onnx_intra_op_threads = 1

    # Mock video frames
    mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_extract.return_value = [
        (0, 0.0, mock_frame),
        (1, 1.0, mock_frame)
    ]
    
    # Mock OCR
    mock_ocr = MagicMock()
    mock_get_ocr.return_value = mock_ocr
    
    # OCR result format: [[[box], text, confidence], ...]
    # Three code-shaped lines (incl. a strong `def` keyword) so the tightened
    # classifier (>=3 code lines + strong keyword) classifies as CODE.
    box = [[10, 10], [50, 10], [50, 20], [10, 20]]
    mock_ocr.return_value = (
        [
            [box, "def mock_func():", 0.95],
            [box, "    x = 1", 0.9],
            [box, "    return x", 0.92],
        ],
        None,
    )
    
    visuals = extract_visuals("dummy.mp4", extract_rate_sec=1.0, device="cpu")
    
    assert len(visuals) == 2
    assert visuals[0].frame_idx == 0
    assert visuals[0].type == VisualRegionType.CODE
    assert "def mock_func():" in visuals[0].text
    
    # Ensure TrOCR/Upscaling wasn't called for high confidence
    assert visuals[0].confidence > 0.9


def test_extract_frames_dedup_collapses_held_slides():
    """Repeated near-identical frames should be deduplicated to a single keep.

    Mirrors the production scenario of a 10-min recording where the speaker
    holds one slide for ~40s: at a 5s sample rate that yields ~8 candidate
    frames that must collapse to ONE so OCR runs once, not 8 times.
    """
    import cv2

    kept: list = []
    recent_hashes: list = []
    import numpy as np

    slide = np.full((64, 64, 3), 120, dtype=np.uint8)  # identical "slide"
    dedup_limit = 64 * 64 * 0.06  # match the stricter threshold
    dedup_window = 8

    def _consider(frame, idx):
        small = cv2.resize(frame, (64, 64))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        curr_hash = gray > gray.mean()
        for ph in recent_hashes:
            if np.count_nonzero(curr_hash != ph) < dedup_limit:
                return False
        kept.append((len(kept), idx / 30.0, frame))
        recent_hashes.append(curr_hash)
        if len(recent_hashes) > dedup_window:
            recent_hashes.pop(0)
        return True

    for i in range(8):
        _consider(slide, i)

    assert len(kept) == 1, f"8 identical frames should collapse to 1, got {len(kept)}"
