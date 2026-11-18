"""Isolated MuPDF/Tesseract worker. Coordinates are fractions of the oriented image."""
import json
from hashlib import sha256
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

import pymupdf


def install_english():
    import httpx
    directory = Path(sys.prefix) / "tessdata"
    directory.mkdir(exist_ok=True)
    path = directory / "eng.traineddata"
    expected = "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"
    if not path.exists() or sha256(path.read_bytes()).hexdigest() != expected:
        url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd/eng.traineddata"
        result = httpx.get(url, timeout=60)
        result.raise_for_status()
        if sha256(result.content).hexdigest() != expected:
            raise ValueError("English OCR data failed its integrity check.")
        with NamedTemporaryFile(dir=directory, delete=False) as tmp:
            tmp.write(result.content)
        Path(tmp.name).replace(path)
    print(f"English OCR data ready at {path}")


def read_lines(payload):
    local = Path(sys.prefix) / "tessdata"
    tessdata = os.getenv("TESSDATA_PREFIX") or (str(local) if local.is_dir() else None)
    pix = pymupdf.Pixmap(payload)
    pix.set_dpi(150, 150)
    pdf = pix.pdfocr_tobytes(language="eng", tessdata=tessdata)
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        page = doc[0]
        lines = {}
        for x0, y0, x1, y1, word, block, line, _ in page.get_text("words", sort=False):
            key = (block, line)
            lines.setdefault(key, []).append({
                "text": word, "box": [round(x0 / page.rect.width, 5), round(y0 / page.rect.height, 5),
                                      round(x1 / page.rect.width, 5), round(y1 / page.rect.height, 5)],
            })
        return list(lines.values())


if __name__ == "__main__":
    if sys.argv[1:] == ["--install-english"]:
        install_english()
    else:
        json.dump(read_lines(sys.stdin.buffer.read()), sys.stdout, ensure_ascii=True)
