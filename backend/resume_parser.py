import fitz  # this is PyMuPDF, installed as pymupdf


def extract_text_from_pdf(filepath: str) -> str:
    """Opens a PDF and pulls out all the plain text from it."""
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text
