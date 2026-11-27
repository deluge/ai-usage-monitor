import pytest

from display_usage.esp32 import dejavu_sans_10, dejavu_sans_11


@pytest.fixture
def font(micropython_modules):
    from display_usage.esp32.font import BitmapFont

    return BitmapFont(dejavu_sans_11)


@pytest.fixture
def framebuffer(micropython_modules):
    from framebuf import FrameBuffer

    return FrameBuffer(bytearray(), 128, 64)


def kerning_pairs(module):
    data = module.KERNING
    return [(chr(data[i]), chr(data[i + 1]), data[i + 2] - 48) for i in range(0, len(data), 3)]


@pytest.mark.parametrize("module", [dejavu_sans_10, dejavu_sans_11])
def test_font_modules(module):
    assert module.FIRST == 32
    assert len(module.GLYPHS) == (127 - 32) * 7
    assert isinstance(module.GLYPHS, bytes), "a tuple per character costs too much RAM"
    assert len(module.KERNING) % 3 == 0
    pairs = [(first, second) for first, second, _ in kerning_pairs(module)]
    assert pairs == sorted(pairs), "kern() needs KERNING sorted for its binary search"


def test_glyph(font):
    record = ord("A") - 32
    advance, x_offset, y_offset, width, height, start_high, start_low = dejavu_sans_11.GLYPHS[
        record * 7 : record * 7 + 7
    ]

    assert font.glyph("A") == (
        advance,
        x_offset - 128,
        y_offset,
        width,
        height,
        start_high << 8 | start_low,
    )


def test_glyph_negative_x_offset_and_large_start(font):
    glyphs = [font.glyph(chr(code)) for code in range(32, 127)]

    assert min(x_offset for _, x_offset, *_ in glyphs) < 0
    assert max(start for *_, start in glyphs) > 255
    starts = [start for *_, start in glyphs]
    assert starts == sorted(starts)


@pytest.mark.parametrize("char", ["ä", "\n", "€"])
def test_unknown_character_is_drawn_as_question_mark(font, char):
    assert font.glyph(char) == font.glyph("?")


def test_kern_finds_every_pair(font):
    pairs = kerning_pairs(dejavu_sans_11)

    assert all(font.kern(first, second) == shift for first, second, shift in pairs)


def test_kern_without_pair(font):
    pairs = {(first, second) for first, second, _ in kerning_pairs(dejavu_sans_11)}
    missing = next((a, b) for a in "AVTo" for b in "AVTo" if (a, b) not in pairs)

    assert font.kern(*missing) == 0
    assert font.kern(" ", " ") == 0  # before the first record
    assert font.kern("~", "~") == 0  # after the last record


def test_advance(font):
    assert font.advance("A", 0) == font.glyph("A")[0]
    assert font.advance("AV", 0) == font.glyph("A")[0] + font.kern("A", "V")


def test_textlength(font):
    text = "Reset 14:30"

    assert font.textlength(text) == sum(font.advance(text, i) for i in range(len(text)))
    assert font.textlength("") == 0


def test_draw_space(font, framebuffer):
    font.draw(framebuffer, 0, 0, " ")

    assert framebuffer.pixels == set()


def test_draw_glyph_position(font, framebuffer):
    _, x_offset, y_offset, width, height, _ = font.glyph("I")

    font.draw(framebuffer, 10, 20, "I")

    xs = {x for x, _ in framebuffer.pixels}
    ys = {y for _, y in framebuffer.pixels}
    assert min(xs) >= 10 + x_offset and max(xs) < 10 + x_offset + width
    assert min(ys) >= 20 + y_offset and max(ys) < 20 + y_offset + height
    assert len(ys) == height  # "I" is one solid stroke


def test_draw_advances_like_textlength(font, framebuffer):
    font.draw(framebuffer, 0, 0, "II")
    two = {x for x, _ in framebuffer.pixels}

    first_stroke = min(two)
    second_stroke = max(two)

    assert second_stroke - first_stroke == font.advance("II", 0)
