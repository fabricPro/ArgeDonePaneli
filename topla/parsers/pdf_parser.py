"""PDF technical spec parser (pdfplumber).

Şimdilik minimal — tam metin döner; ileride width/cert/weight selectorleri eklenir.
"""

import pdfplumber


def parse_pdf(file_path: str) -> dict:
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return {"full_text": "\n\n".join(text_parts)}
