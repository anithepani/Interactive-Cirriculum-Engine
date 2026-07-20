import json

from frame_extractor import FrameExtractor

VIDEO = "/home/mahmed/Documents/Interactive Curriculum Engine/Learn Python In 10 Minutes !! - AmanBytes (1080p, h264).mp4"

extractor = FrameExtractor(VIDEO)

frames = extractor.extract_frames()

print(f"Extracted {len(frames)} frames")

print(json.dumps(frames[:5], indent=4))