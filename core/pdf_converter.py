"""
pdf_converter.py - Converte PDFs em imagens PIL para auditoria IA.
"""

from __future__ import annotations
import io
from typing import List
from PIL import Image

def pdf_to_images(pdf_path: str) -> List[Image.Image]:
    """
    Converte todas as páginas de um PDF em uma lista de imagens PIL.
    Usa a biblioteca fitz (PyMuPDF) por ser rápida e não depender de binários externos como poppler.
    """
    try:
        import fitz # PyMuPDF
    except ImportError:
        raise ImportError("A biblioteca 'pymupdf' é necessária para auditar PDFs existentes. Instale com: pip install pymupdf")

    images = []
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Aumentar a escala para melhor legibilidade (DPI 300 aprox)
        zoom = 2.0 
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        images.append(img.convert("RGB"))
        
    doc.close()
    return images
