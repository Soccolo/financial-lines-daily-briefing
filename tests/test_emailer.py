from briefing.emailer import render_formula_png


def test_render_formula_png_embeds_a_png():
    image = render_formula_png(r"p = \frac{x}{n}")
    assert image is not None
    assert image.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_formula_png_returns_none_for_empty_formula():
    assert render_formula_png("") is None
