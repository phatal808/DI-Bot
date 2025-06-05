import json
import os
from pathlib import Path

try:
    from PIL import Image
    import pytesseract
except Exception as e:
    print("Warning: OCR libraries not available -", e)
    Image = None
    pytesseract = None

def process_image(image_path: str) -> str:
    """Run OCR on the image and return the text"""
    if Image is None or pytesseract is None:
        raise RuntimeError("Required libraries not installed")
    text = pytesseract.image_to_string(Image.open(image_path))
    return text

def save_json(text: str, output_path: str = "data/output.json") -> None:
    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"text": text}, f, indent=2)

def main(image_path: str):
    text = process_image(image_path)
    save_json(text)
    print("Processed", image_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python process.py <image>")
        sys.exit(1)
    main(sys.argv[1])
