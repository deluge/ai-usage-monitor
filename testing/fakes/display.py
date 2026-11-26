from display_usage.display import BaseDisplay


class FakeDisplay(BaseDisplay):
    """Records what would have been drawn instead of drawing it."""

    def __init__(self):
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
