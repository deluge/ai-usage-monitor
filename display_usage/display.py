from display_usage.utils import (
    Timezone,
    format_reset_current,
    format_reset_weekly,
    parse_reset,
)


class BaseDisplay:
    """Screen layout for a 128×64 display, drawn with a few primitives.

    Subclasses (display_usage/pizerow/, display_usage/esp32/) set up the hardware and fonts
    (self.font, self.font_small) and implement clear(), show(), text(), textlength()
    and rectangle(). Coordinates work like PIL: text() takes the top left corner and
    rectangle() includes both end points.
    """

    WIDTH = 128
    HEIGHT = 64
    FONT_SIZE = 11
    SMALL_FONT_SIZE = 10
    LINE_HEIGHT = 14
    BAR_LEFT = 52  # leaves room for the "Current" / "Weekly" label
    BAR_HEIGHT = 7

    def __init__(self, timezone=None):
        self.timezone = timezone or Timezone()

    def clear(self):
        raise NotImplementedError

    def show(self):
        raise NotImplementedError

    def text(self, x, y, text, font):
        raise NotImplementedError

    def textlength(self, text, font):
        raise NotImplementedError

    def rectangle(self, left, top, right, bottom, fill=False):
        raise NotImplementedError

    def show_message(self, *lines):
        self.clear()
        for i, line in enumerate(lines):
            self.text(0, i * self.LINE_HEIGHT, line, self.font)
        self.show()

    def show_loading(self, dots=3):
        self.clear()
        self.text(0, 26, "Loading" + "." * dots, self.font)
        self.show()

    def show_usage(self, usage):
        five_hour = usage.get("five_hour") or {}
        seven_day = usage.get("seven_day") or {}
        current_reset = format_reset_current(
            parse_reset(five_hour.get("resets_at")), self.timezone
        )
        weekly_reset = format_reset_weekly(
            parse_reset(seven_day.get("resets_at")), self.timezone
        )
        self.clear()
        self._draw_block(0, "Current", five_hour.get("utilization"), current_reset)
        self.rectangle(0, 31, self.WIDTH - 1, 31, fill=True)
        self._draw_block(34, "Weekly", seven_day.get("utilization"), weekly_reset)
        self.show()

    def _draw_block(self, top, label, percent, reset_text):
        """Draw "label [bar] xx%" with the reset time in the line below."""
        percent = max(0.0, min(100.0, percent or 0.0))
        percent_text = f"{percent:.0f}%"
        percent_left = self.WIDTH - self.textlength(percent_text, self.font)

        self.text(0, top, label, self.font)
        self._draw_bar(top + 3, right=percent_left - 4, percent=percent)
        self.text(percent_left, top, percent_text, self.font)
        self.text(0, top + self.LINE_HEIGHT, reset_text, self.font_small)

    def _draw_bar(self, top, right, percent):
        left, bottom = self.BAR_LEFT, top + self.BAR_HEIGHT
        self.rectangle(left, top, right, bottom)
        fill_width = int((right - left - 2) * percent / 100)
        if fill_width > 0:
            self.rectangle(left + 1, top + 1, left + 1 + fill_width, bottom - 1, fill=True)
