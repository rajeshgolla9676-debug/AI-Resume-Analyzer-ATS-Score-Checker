from pathlib import Path
import fitz
from docx import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF and DOCX files are supported.")
    if ext == ".pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
    else:
        import io
        document = Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        text = "\n".join(parts)
    if not text.strip():
        raise ValueError("No readable text found. Please upload a text-based PDF or DOCX.")
    return text[:100000]
