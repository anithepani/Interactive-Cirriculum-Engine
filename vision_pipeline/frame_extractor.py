import cv2
import os


class FrameExtractor:

    def __init__(self, video_path, output_dir="/home/mahmed/Documents/Interactive Curriculum Engine/Text_Video_Extraction/output/frames"):
        self.video_path = video_path
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

    def extract_frames(self):

        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            raise Exception("Cannot open video.")

        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_interval = int(fps)

        frame_number = 0
        saved_index = 0

        metadata = []

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            if frame_number % frame_interval == 0:

                timestamp = frame_number / fps

                filename = f"frame_{saved_index:05d}.jpg"

                filepath = os.path.join(
                    self.output_dir,
                    filename
                )

                cv2.imwrite(filepath, frame)

                metadata.append({
                    "frame_idx": saved_index,
                    "ts": round(timestamp, 2),
                    "frame_path": filepath
                })

                saved_index += 1

            frame_number += 1

        cap.release()

        return metadata