# M3 - Visual Content Extraction

PaddleOCR 2.7 (primary) + TrOCR (fallback) + CLIP keyframe dedup + LayoutLMv3 region
detection + Real-ESRGAN upscaling + tree-sitter code sanitization. Produces OCR'd code
blocks, slides, diagrams with confidence.

**Lead:** Ahmed · **Support:** Aryan (fusion)

See [`libs/ai/vision/src/ice_vision/__init__.py`](src/ice_vision/__init__.py) for the full spec.
