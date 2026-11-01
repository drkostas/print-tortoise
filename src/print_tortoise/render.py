"""Draw a PDF with three engines side by side, and mark where they disagree.

    print-tortoise <file.pdf> [--out DIR] [--dpi 150] [--strict]

Every page is rendered with MuPDF, Ghostscript and Apple's engine (CoreGraphics, what Preview and
Quick Look show), each is compared with MuPDF in blocks about 7 mm square, and one picture per page
shows the three side by side with the disagreeing blocks outlined in red. An engine this machine does
not have is left out and named.

What it reports:

- the transparency the page uses (`check.transparency`);
- for each page and engine, the share of blocks whose average colour differs from MuPDF's by more
  than 30 of 255. A wrong glow is a solid block several millimetres wide, so it shows, while text
  drawn a little heavier averages out inside a block.

Ghostscript draws hairline patterns (a guilloche, a fine wave) heavier than the other two even on a
page with no transparency, about 1% of the blocks on one such page at 150 dpi, so its share is reported
and never fails. `--strict` fails on Apple's engine only. Nothing here can draw what a printer's own
interpreter does, so a page with no transparency at all is the only one this can vouch for.

Exit 0 when the PDF uses no transparency (and, with --strict, Apple's engine agrees on every page),
1 when it does not, 2 when it could not run.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .check import transparency

ENGINES = ("mupdf", "ghostscript", "coregraphics")
SWIFT = Path(__file__).with_name("qrender.swift")
CACHE = Path.home() / "Library/Caches/print-tortoise"
_ENV = None             # the caller's own environment
BLOCK_MM = 7.0
THRESHOLD = 30          # of 255, on a block's average colour
STRICT_SHARE = 0.005    # Apple's engine may differ on half a percent of the blocks, no more


def qrender(cache: Path = CACHE) -> Path | None:
    """The compiled CoreGraphics renderer, built from qrender.swift once per version of it; None
    when there is no Swift compiler (not a Mac) or it does not compile."""
    swiftc = shutil.which("swiftc")
    if swiftc is None or not SWIFT.is_file():
        return None
    binary = Path(cache) / f"qrender-{hashlib.sha256(SWIFT.read_bytes()).hexdigest()[:12]}"
    if not binary.is_file():
        binary.parent.mkdir(parents=True, exist_ok=True)
        tmp = binary.with_suffix(".tmp")
        r = subprocess.run([swiftc, "-O", str(SWIFT), "-o", str(tmp)], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return None
        tmp.rename(binary)
    return binary


def render(pdf: Path, out: Path, dpi: int = 150) -> dict[str, list[Path]]:
    """Each engine's pages as PNG files in `out`, in page order; an engine that is not on this
    machine, or that fails, is left out rather than guessed."""
    out.mkdir(parents=True, exist_ok=True)
    got: dict[str, list[Path]] = {}
    import pymupdf
    with pymupdf.open(str(pdf)) as doc:
        pages = []
        for i, page in enumerate(doc, 1):
            p = out / f"mupdf-p{i}.png"
            page.get_pixmap(dpi=dpi).save(str(p))
            pages.append(p)
    got["mupdf"] = pages
    gs = shutil.which("gs")
    if gs:
        r = subprocess.run([gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m",
                            "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4", f"-r{dpi}",
                            "-o", str(out / "ghostscript-p%d.png"), str(pdf)],
                           capture_output=True, text=True, timeout=300, env=_ENV)
        if r.returncode == 0:
            got["ghostscript"] = [out / f"ghostscript-p{i}.png" for i in range(1, len(pages) + 1)]
    q = qrender()
    if q:
        r = subprocess.run([str(q), str(pdf), str(out / "coregraphics"), str(dpi)],
                           capture_output=True, text=True, timeout=300, env=_ENV)
        if r.returncode == 0:
            got["coregraphics"] = [out / f"coregraphics-p{i}.png" for i in range(1, len(pages) + 1)]
    return {e: ps for e, ps in got.items() if all(p.is_file() for p in ps)}


def disagreement(a, b, block: int, threshold: int = THRESHOLD):
    """(the share of blocks whose average colour differs by more than `threshold`, a mask of
    those blocks) for two pictures of one page, as numpy arrays; cropped to the smaller one, since
    engines round a page's size differently by a pixel."""
    import numpy as np
    h, w = min(a.shape[0], b.shape[0]) // block * block, min(a.shape[1], b.shape[1]) // block * block
    pool = lambda x: x[:h, :w, :3].astype(np.float32).reshape(h // block, block, w // block, block, 3).mean(axis=(1, 3))  # noqa: E731
    bad = np.abs(pool(a) - pool(b)).max(axis=2) > threshold
    return float(bad.mean()) if bad.size else 0.0, bad


def check(pdf: Path, out: Path | None = None, dpi: int = 150) -> dict:
    """The transparency the PDF uses, and for each page how far each engine is from MuPDF, with a
    side-by-side picture of each page written to `out` (a new folder when none is given)."""
    import numpy as np
    from PIL import Image, ImageDraw
    out = Path(out) if out else Path(tempfile.mkdtemp(prefix="print-tortoise-"))
    shots = render(Path(pdf), out, dpi)
    block = max(4, round(BLOCK_MM / 25.4 * dpi))
    pages = []
    for i, base_png in enumerate(shots["mupdf"], 1):
        base = np.asarray(Image.open(base_png).convert("RGB"))
        row = {"page": i, "share": {}, "picture": str(out / f"page-{i}-engines.png")}
        tiles = []
        for engine in ENGINES:
            if engine not in shots:
                continue
            img = Image.open(shots[engine][i - 1]).convert("RGB")
            if engine != "mupdf":
                share, bad = disagreement(np.asarray(img), base, block)
                row["share"][engine] = round(share, 4)
                draw = ImageDraw.Draw(img)
                for y, x in zip(*np.where(bad)):
                    draw.rectangle([x * block, y * block, (x + 1) * block - 1, (y + 1) * block - 1],
                                   outline=(255, 0, 0), width=2)
            tiles.append(img)
        sheet = Image.new("RGB", (sum(t.width for t in tiles), max(t.height for t in tiles)), "white")
        x = 0
        for t in tiles:
            sheet.paste(t, (x, 0))
            x += t.width
        sheet.save(row["picture"])
        pages.append(row)
    return {"transparency": transparency(pdf), "engines": sorted(shots), "pages": pages,
            "out": str(out)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="print-tortoise", description="Draw a PDF with three engines side by side, and mark where they disagree.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--strict", action="store_true",
                    help="also fail when Apple's engine disagrees with MuPDF on any page")
    a = ap.parse_args(argv)
    if not a.pdf.is_file():
        print(f"no such file: {a.pdf}", file=sys.stderr)
        return 2
    r = check(a.pdf, a.out, a.dpi)
    for line in r["transparency"]:
        print(f"REFUSED: {line}")
    for p in r["pages"]:
        shares = ", ".join(f"{e} {v:.1%}" for e, v in p["share"].items())
        print(f"page {p['page']}: blocks unlike MuPDF: {shares or 'no other engine ran'}  {p['picture']}")
    missing = [e for e in ENGINES if e not in r["engines"]]
    if missing:
        print(f"not drawn here: {', '.join(missing)}")
    print("the printer's own interpreter is a fourth engine, and nothing here draws it")
    apple = any(p["share"].get("coregraphics", 0) > STRICT_SHARE for p in r["pages"])
    return 1 if r["transparency"] or (a.strict and apple) else 0


if __name__ == "__main__":
    raise SystemExit(main())
