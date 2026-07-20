"""Tests for M3 vision extraction."""

import numpy as np
import pytest
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
    # Mock settings values
    mock_settings.vision.max_workers = 1
    mock_settings.vision.extract_rate_sec = 1.0
    mock_settings.vision.dedup_threshold = 0.08
    mock_settings.vision.ocr_confidence_threshold = 0.7
    mock_settings.vision.max_frames = 150
    mock_settings.vision.enable_heavy_fallbacks = False

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
    box = [[10, 10], [50, 10], [50, 20], [10, 20]]
    mock_ocr.return_value = (
        [
            [box, "def mock_func():", 0.95],
            [box, "    pass", 0.9]
        ],
        None
    )
    
    visuals = extract_visuals("dummy.mp4", extract_rate_sec=1.0, device="cpu")
    
    assert len(visuals) == 2
    assert visuals[0].frame_idx == 0
    assert visuals[0].type == VisualRegionType.CODE
    assert "def mock_func():" in visuals[0].text
    
    # Ensure TrOCR/Upscaling wasn't called for high confidence
    assert visuals[0].confidence > 0.9
