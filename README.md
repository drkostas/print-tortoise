# print-tortoise

A PDF printed from HTML can look right in one PDF engine and wrong in another. A CSS glow that MuPDF draws as a glow can become a solid coloured block in Apple's Preview. This package finds that before you print.

```bash
pip install print-tortoise
print-tortoise sheet.pdf --out pictures
```

```
REFUSED: page 1 has 1 partly transparent fill or line, which PDF engines do not all draw the same way
page 1: blocks unlike MuPDF: ghostscript 0.0%, coregraphics 0.0%  pictures/page-1-engines.png
the printer's own interpreter is a fourth engine, and nothing here draws it
```

Each picture shows the page from each engine side by side, with the blocks that differ outlined in red.

```python
from print_tortoise import transparency, check

transparency("sheet.pdf")      # one sentence per page that uses transparency, [] when none does
check("sheet.pdf", "pictures") # the same, each engine's share of differing blocks, and the pictures
```

## What it needs

MuPDF comes with the package. Ghostscript (`gs`) and a Swift compiler (`swiftc`, for Apple's engine on a Mac) are used when they are present, and an engine that is missing is left out and named.

## Exit codes

The command exits 0 when the PDF uses no transparency, 1 when it does, and 2 when it could not run. With `--strict` it also exits 1 when Apple's engine differs from MuPDF on more than half a percent of a page's blocks.

## What it cannot do

A printer's own interpreter is another engine, and nothing here can draw what it does. A page with no transparency at all is the only one this can vouch for.

## License

This package's code is MIT. It depends on PyMuPDF, which is under the AGPL or a commercial license, so check that license fits your use.

Named after the Truth Tortoise from Rick and Morty, which shows you everything. This one only shows you the page your printer will get wrong.
