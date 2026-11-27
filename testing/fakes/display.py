from display_usage.display import BaseDisplay


class FakeDisplay(BaseDisplay):
    """Records what would have been shown instead of drawing it."""

    def __init__(self):
        super().__init__()
        self.calls = []

    def show_message(self, *lines):
        self.calls.append(("message", lines))

    def show_loading(self, dots=3):
        self.calls.append(("loading", dots))

    def show_usage(self, usage, updated_at=None):
        if updated_at is None:
            self.calls.append(("usage", usage))
        else:
            self.calls.append(("usage", usage, updated_at))

    @property
    def last_call(self):
        return self.calls[-1]


class PrimitivesDisplay(BaseDisplay):
    """Records the drawing primitives BaseDisplay calls, to test the screen layout.

    Every character is 6 pixels wide.
    """

    font = "font"
    font_small = "small"

    def __init__(self, timezone=None):
        super().__init__(timezone)
        self.calls = []

    def clear(self):
        self.calls = [("clear",)]

    def show(self):
        self.calls.append(("show",))

    def text(self, x, y, text, font):
        self.calls.append(("text", x, y, text, font))

    def textlength(self, text, font):
        return 6 * len(text)

    def rectangle(self, left, top, right, bottom, fill=False):
        self.calls.append(("rectangle", left, top, right, bottom, fill))

    def texts(self):
        return [call[3] for call in self.calls if call[0] == "text"]

    def rectangles(self):
        return [call[1:] for call in self.calls if call[0] == "rectangle"]
