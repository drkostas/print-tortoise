import pikepdf
import pymupdf

from print_tortoise import transparency


def test_a_plain_pdf_uses_none(build):
    assert transparency(build("plain", 2)) == []


def test_a_transparent_fill_is_named_with_its_page(build):
    got = transparency(build("faded", opacity=0.5))
    assert len(got) == 1 and got[0].startswith("page 1 has 1 partly transparent fill or line")


def test_an_image_with_alpha_is_not_refused(build):
    assert transparency(build("image", image_alpha=True)) == []


def test_a_soft_mask_is_named_on_the_page_that_uses_it(build, tmp_path):
    masked = tmp_path / "masked.pdf"
    with pikepdf.open(build("plain", 2)) as pdf:
        page = pdf.pages[1]
        group = pikepdf.Stream(pdf, b"0.5 g 0 0 300 200 re f")
        group.Type, group.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
        group.BBox = [0, 0, 300, 200]
        group.Group = pikepdf.Dictionary(S=pikepdf.Name.Transparency, CS=pikepdf.Name.DeviceGray)
        state = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.ExtGState,
            SMask=pikepdf.Dictionary(Type=pikepdf.Name.Mask, S=pikepdf.Name.Luminosity, G=group)))
        name = page.add_resource(state, pikepdf.Name.ExtGState, prefix="GS")
        page.contents_add(pikepdf.Stream(pdf, f"q {name} gs 1 0 0 rg 20 130 120 40 re f Q".encode()))
        pdf.save(masked)
    got = transparency(masked)
    assert len(got) == 1 and got[0].startswith("page 2 uses 1 soft mask")


def test_transparency_inside_a_placed_form_is_found(build, tmp_path):
    outer = pymupdf.open()
    outer.new_page(width=600, height=400).show_pdf_page(pymupdf.Rect(0, 0, 300, 200),
                                                        pymupdf.open(build("faded", opacity=0.5)), 0)
    nested = tmp_path / "nested.pdf"
    outer.save(str(nested))
    got = transparency(nested)
    assert len(got) == 1 and "partly transparent" in got[0]


def test_a_file_that_is_no_pdf_is_a_reason(tmp_path):
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"%PDF-1.4\nnot a pdf at all\n")
    got = transparency(junk)
    assert len(got) == 1 and "could not read" in got[0]
