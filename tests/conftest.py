from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def build(tmp_path):
    """A small PDF: words and a filled box on each page, optionally transparent or with an image."""
    def _build(name: str, pages: int = 1, *, opacity: float = 1.0, image_alpha: bool = False) -> Path:
        doc = pymupdf.open()
        for _ in range(pages):
            page = doc.new_page(width=300, height=200)
            page.insert_text((20, 40), "Six words", fontsize=18)
            page.draw_rect(pymupdf.Rect(20, 60, 200, 120), color=(0.5, 0.2, 0.8), fill=(0.9, 0.85, 1.0),
                           fill_opacity=opacity)
            if image_alpha:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), 1)
                pix.clear_with(200)
                page.insert_image(pymupdf.Rect(220, 60, 260, 100), pixmap=pix)
        path = tmp_path / f"{name}.pdf"
        doc.save(str(path))
        return path
    return _build
