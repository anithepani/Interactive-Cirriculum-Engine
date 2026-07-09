import easyocr


class OCRExtractor:

    def __init__(self):

        print("Loading EasyOCR...")

        self.reader = easyocr.Reader(
            ['en'],
            gpu=False
        )

        print("EasyOCR Ready.")

    def extract_text(self, image_path):

        result = self.reader.readtext(
            image_path,
            detail=0,
            paragraph=True
        )

        return "\n".join(result)