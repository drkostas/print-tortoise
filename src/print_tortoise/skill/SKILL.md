---
name: print-tortoise
description: Use when a PDF will be printed or read on more than one viewer, above all a PDF made from HTML with CSS shadows, glows or gradients, or when a page looks right in one viewer and shows solid coloured blocks in another. Draws it with MuPDF, Ghostscript and Apple's engine, marks where they disagree, and names the transparency that makes them disagree. Python package `print-tortoise`, imported as `print_tortoise`.
---

# Checking a PDF before it prints

```bash
print-tortoise sheet.pdf --out pictures --strict
```

Open each `page-N-engines.png` and look at it before saying the page is fine. Exit 0 means no transparency, and with `--strict` that Apple's engine agrees too.

## Rules

- Fix a refused page at its source. Remove the CSS `box-shadow`, `filter`, `opacity` and gradients that fade to transparent, and render the PDF again.
- An image's own alpha is allowed, because every engine draws it the same way.
- Ghostscript's share is reported and never fails, because it draws hairlines heavier even on a clean page.
- A missing engine is named in the output, so read that line before trusting the result.
- A printer's interpreter is another engine, and nothing here draws it.
