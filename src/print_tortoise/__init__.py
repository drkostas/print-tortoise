"""Find the PDF page one engine draws wrong, before it prints."""
from .check import transparency
from .render import check, disagreement, render

__version__ = "0.1.0"
__all__ = ["check", "disagreement", "render", "transparency"]
