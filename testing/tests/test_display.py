import pytest
from freezegun import freeze_time

from conftest import NOW
from display_usage.display import BaseDisplay
from display_usage.utils import Timezone
from testing.fakes.display import PrimitivesDisplay


USAGE = {
    "five_hour": {"utilization": 42.0, "resets_at": "2026-11-24T14:30:00+00:00"},
    "seven_day": {"utilization": 87.5, "resets_at": "2026-11-27T09:00:00+00:00"},
}


@pytest.fixture
def screen():
    return PrimitivesDisplay()


def bar_fill(screen, top):
    """Right edge of the filled part of the bar starting at top, or None if empty."""
    for left, rect_top, right, _, fill in screen.rectangles():
        if fill and rect_top == top + 1:
            return right
    return None


def test_default_timezone():
    assert BaseDisplay().timezone.utc_offset is None


def test_timezone():
    timezone = Timezone(1)

    assert BaseDisplay(timezone).timezone is timezone


@pytest.mark.parametrize(
    "method, args",
    [
        ("clear", ()),
        ("show", ()),
        ("text", (0, 0, "x", None)),
        ("textlength", ("x", None)),
        ("rectangle", (0, 0, 1, 1)),
    ],
)
def test_primitives_must_be_implemented(method, args):
    with pytest.raises(NotImplementedError):
        getattr(BaseDisplay(), method)(*args)


def test_show_message(screen):
    screen.show_message("First", "Second")

    assert screen.calls == [
        ("clear",),
        ("text", 0, 0, "First", "font"),
        ("text", 0, 14, "Second", "font"),
        ("show",),
    ]


@pytest.mark.parametrize("dots, text", [(1, "Loading."), (3, "Loading...")])
def test_show_loading(screen, dots, text):
    screen.show_loading(dots)

    assert screen.calls == [("clear",), ("text", 0, 26, text, "font"), ("show",)]


def test_show_loading_default_dots(screen):
    screen.show_loading()

    assert screen.texts() == ["Loading..."]


@freeze_time("2026-11-24 12:00:00")
class TestShowUsage:
    def test_layout(self, screen):
        screen.show_usage(USAGE)

        assert screen.calls[0] == ("clear",)
        assert screen.calls[-1] == ("show",)
        # "42%" is 18 px wide: it starts at 110 and the bar ends 4 px before it.
        # The bar is 52 px wide inside, 42% of it fills 21 px.
        assert screen.calls[1:-1] == [
            ("text", 0, 0, "Current", "font"),
            ("rectangle", 52, 3, 106, 10, False),
            ("rectangle", 53, 4, 53 + 21, 9, True),
            ("text", 110, 0, "42%", "font"),
            ("text", 0, 14, "Reset 14:30 (2h30)", "small"),
            ("rectangle", 0, 31, 127, 31, True),
            ("text", 0, 34, "Weekly", "font"),
            ("rectangle", 52, 37, 106, 44, False),
            ("rectangle", 53, 38, 53 + 45, 43, True),
            ("text", 110, 34, "88%", "font"),
            ("text", 0, 48, "Reset Fri 27.11. 09:00", "small"),
        ]

    def test_uses_timezone(self):
        screen = PrimitivesDisplay(Timezone(1))

        screen.show_usage(USAGE)

        assert "Reset 15:30 (2h30)" in screen.texts()
        assert "Reset Fri 27.11. 10:00" in screen.texts()

    @pytest.mark.parametrize(
        "utilization, text, fill",
        [(0, "0%", None), (None, "0%", None), (100, "100%", 53 + 46), (250, "100%", 53 + 46)],
    )
    def test_utilization_is_clamped(self, screen, utilization, text, fill):
        screen.show_usage({"five_hour": {"utilization": utilization}})

        assert screen.texts()[1] == text
        assert bar_fill(screen, 3) == fill

    def test_expired_window_is_empty(self, screen):
        screen.show_usage(
            {"five_hour": {"utilization": 90, "resets_at": "2026-11-24T11:59:00+00:00"}}
        )

        assert screen.texts()[:3] == ["Current", "0%", "Reset: --"]
        assert bar_fill(screen, 3) is None

    def test_old_data_replaces_weekly_reset(self, screen):
        updated_at = NOW - 3600

        screen.show_usage(USAGE, updated_at=updated_at)

        assert screen.texts()[-1] == "Data from Tue 11:00"
        assert "Reset Fri 27.11. 09:00" not in screen.texts()
        assert "Reset 14:30 (2h30)" in screen.texts()

    def test_old_data_uses_timezone(self):
        screen = PrimitivesDisplay(Timezone(1))

        screen.show_usage(USAGE, updated_at=NOW - 3600)

        assert screen.texts()[-1] == "Data from Tue 12:00"

    def test_missing_data(self, screen):
        screen.show_usage({"five_hour": None})

        assert screen.texts() == ["Current", "0%", "Reset: --", "Weekly", "0%", "Reset: --"]
