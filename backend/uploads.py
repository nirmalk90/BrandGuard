from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

import pymupdf
from docx import Document
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

MAX_BYTES = 5 * 1024 * 1024


def read_text(suffix, payload):
    if suffix == ".txt":
        text = payload.decode("utf-8-sig")
    elif suffix == ".pdf" and payload.startswith(b"%PDF-"):
        with pymupdf.open(stream=payload, filetype="pdf") as document:
            if document.needs_pass or document.page_count > 50:
                raise ValueError("PDF must be unlocked and have at most 50 pages.")
            text = "\n".join(page.get_text() for page in document)
    elif suffix == ".docx":
        with ZipFile(BytesIO(payload)) as archive:
            members = archive.infolist()
            if len(members) > 500 or sum(item.file_size for item in members) > 20 * 1024 * 1024:
                raise ValueError("Expanded document is too large.")
            if "word/document.xml" not in archive.namelist():
                raise ValueError("Invalid DOCX structure.")
        document = Document(BytesIO(payload))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        for table in document.tables:
            text += "\n" + "\n".join(" | ".join(cell.text for cell in row.cells) for row in table.rows)
    else:
        raise ValueError("Unsupported file.")
    return text.strip()


async def extract(upload: UploadFile):
    filename = PurePosixPath((upload.filename or "").replace("\\", "/")).name
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".txt", ".pdf", ".docx"}:
        raise HTTPException(415, "Upload a TXT, PDF or DOCX file.")
    payload = await upload.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "The file exceeds the 5 MB limit.")
    try:
        content = await run_in_threadpool(read_text, suffix, payload)
    except Exception:
        raise HTTPException(422, "Unable to read this document. Check the format, size and PDF page limit.") from None
    if not content or "\x00" in content:
        raise HTTPException(422, "The document has no readable text. Scanned documents require OCR.")
    if len(content) > 20000:
        raise HTTPException(422, "Extracted text exceeds 20,000 characters.")
    return {"title": filename[:160], "content": content}
