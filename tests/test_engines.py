from pathlib import Path

import numpy as np

from print_tortoise import check, disagreement
from print_tortoise.render import main

WHITE = np.full((400, 600, 3), 255, np.uint8)


def test_equal_pictures_agree():
    assert disagreement(WHITE, WHITE, 20)[0] == 0.0


def test_a_solid_block_is_found_block_by_block():
    block = np.array(WHITE)
    block[100:220, 150:400] = (124, 58, 237)
    share, bad = disagreement(block, WHITE, 20)
    assert 0.1 < share < 0.15 and bad.sum() == 6 * 13
    assert disagreement(block[:-1, :-1], WHITE, 20)[0] > 0.1     # engines round a page's size differently


def test_scattered_dark_pixels_average_out():
    noise = np.array(WHITE)
    noise[::7, ::5] = 0
    assert disagreement(noise, WHITE, 20)[0] == 0.0


def test_every_page_is_drawn_side_by_side(build, tmp_path):
    r = check(build("plain", 2), tmp_path / "render", dpi=50)
    assert "mupdf" in r["engines"] and len(r["pages"]) == 2
    assert all(Path(p["picture"]).is_file() for p in r["pages"])
    assert r["transparency"] == []
    if "coregraphics" in r["engines"]:
        assert [p["share"]["coregraphics"] for p in r["pages"]] == [0.0, 0.0]


def test_the_command_exits_by_what_it_found(build, tmp_path):
    assert main([str(build("plain")), "--out", str(tmp_path / "a"), "--dpi", "40"]) == 0
    assert main([str(build("faded", opacity=0.5)), "--out", str(tmp_path / "b"), "--dpi", "40"]) == 1
    assert main([str(tmp_path / "nothing.pdf")]) == 2
