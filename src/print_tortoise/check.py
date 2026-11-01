"""Name the transparency a PDF uses outside images, which PDF engines draw differently.

A PDF printed from HTML turns CSS glows (box-shadow) into soft masks (/SMask in an ExtGState) and
partly transparent fills (/ca, /CA below 1). MuPDF draws them as glows. Apple's engine (Preview, Quick
Look, CoreGraphics) can draw each glow as a hard coloured rectangle over the words, and Ghostscript
10.02 drops gradients that end in transparent. A printer's own interpreter is one more engine nobody
sees. So a page that must print the same everywhere should not lean on transparency at all. An image's
own soft mask (a PNG's alpha) is left alone, because each engine draws it the same way.
"""
from __future__ import annotations

from pathlib import Path


def _states(pikepdf, resources, seen: set) -> list:
    """Every ExtGState reachable from a resources dictionary: its own, and those of the forms and
    patterns it uses (a soft mask's own group is a form too), each object once."""
    out = []
    if not isinstance(resources, pikepdf.Dictionary):
        return out
    for _name, gs in (resources.get("/ExtGState") or {}).items():
        key = gs.objgen if gs.is_indirect else id(gs)
        if key not in seen:
            seen.add(key)
            out.append(gs)
            sm = gs.get("/SMask")
            if isinstance(sm, pikepdf.Dictionary) and isinstance(sm.get("/G"), pikepdf.Stream):
                out += _states(pikepdf, sm["/G"].get("/Resources"), seen)
    for kind in ("/XObject", "/Pattern"):
        for _name, obj in (resources.get(kind) or {}).items():
            key = obj.objgen if obj.is_indirect else id(obj)
            if key in seen or obj.get("/Subtype") == "/Image":
                continue                      # an image's own /SMask is its alpha, not a state
            seen.add(key)
            out += _states(pikepdf, obj.get("/Resources"), seen)
            if obj.get("/ExtGState") is not None:            # a shading pattern's own state
                out += _states(pikepdf, pikepdf.Dictionary({"/ExtGState": pikepdf.Dictionary(
                    {"/P": obj["/ExtGState"]})}), seen)
    return out


def transparency(pdf: str | Path) -> list[str]:
    """What a printed page must not use, one plain sentence per page that uses it; [] when the
    PDF uses none. A file that cannot be read as a PDF is a reason too, since it cannot be checked."""
    import pikepdf
    try:
        doc = pikepdf.open(str(pdf))
    except (pikepdf.PdfError, OSError) as e:
        return [f"could not read {Path(pdf).name} as a PDF to check it ({str(e)[:80]})"]
    found = []
    with doc:
        for n, page in enumerate(doc.pages, 1):
            masks = alpha = 0
            for gs in _states(pikepdf, page.obj.get("/Resources"), set()):
                sm = gs.get("/SMask")
                if sm is not None and sm != pikepdf.Name("/None"):
                    masks += 1
                alpha += sum(1 for k in ("/ca", "/CA") if k in gs and float(gs[k]) < 1)
            if masks:
                found.append(f"page {n} uses {masks} soft mask{'s' * (masks != 1)} (a glow or a fade), "
                             "which Apple's PDF engine draws as a solid block")
            if alpha:
                found.append(f"page {n} has {alpha} partly transparent "
                             f"{'fill or line' if alpha == 1 else 'fills or lines'}, which PDF engines "
                             "do not all draw the same way")
    return found
