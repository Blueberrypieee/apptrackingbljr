import os

MAX_TEXT_LENGTH = 20000



def extract_text(file_path: str) -> str:
    """
    Ekstrak teks dari file PDF, DOCX, DOC, TXT, MD.
    Return string teks hasil ekstrak, dibatasi MAX_TEXT_LENGTH karakter.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = _extract_pdf(file_path)
    elif ext in (".docx", ".doc"):
        text = _extract_docx(file_path)
    elif ext in (".txt", ".md"):
        text = _extract_txt(file_path)
    else:
        raise ValueError(f"Format file '{ext}' tidak didukung.")

    return text[:MAX_TEXT_LENGTH]

def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Gagal baca PDF: {e}")

def _extract_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Gagal baca DOCX: {e}")

def _extract_txt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        raise RuntimeError(f"Gagal baca TXT: {e}")

