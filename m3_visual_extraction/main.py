import os
import json

from ocr import OCRExtractor
from classifier import FrameClassifier
from language_detector import LanguageDetector

FRAME_DIR = "/home/mahmed/Documents/Interactive Curriculum Engine/vision_pipeline/output/frames"
OUTPUT_DIR = "/home/mahmed/Documents/Interactive Curriculum Engine/m3_visual_extraction/output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

ocr = OCRExtractor()
classifier = FrameClassifier()
lang_detector = LanguageDetector()

results = []

# Get only the first 10 frames for testing
frames = sorted([
    f for f in os.listdir(FRAME_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
])[:10]

print(f"Found {len(frames)} frames. Processing first {len(frames)} frames...\n")

for idx, frame in enumerate(frames):

    image_path = os.path.join(FRAME_DIR, frame)

    print(f"[{idx + 1}/{len(frames)}] Processing {frame}")

    try:
        text = ocr.extract_text(image_path)

        print(f"OCR extracted {len(text)} characters")

        item = {
            "frame_idx": idx,
            "ts": idx,
            "type": classifier.classify(text),
            "text": text,
            "code_lang": lang_detector.detect(text)
        }

        results.append(item)

    except Exception as e:
        print(f"Error processing {frame}: {e}")

with open(
    os.path.join(OUTPUT_DIR, "visual_items.json"),
    "w",
    encoding="utf-8"
) as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"\nProcessed {len(results)} frames.")
print(f"Saved to {os.path.join(OUTPUT_DIR, 'visual_items.json')}")