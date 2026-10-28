import datetime
import os
import sys

from PIL import ImageFont


FONT_DIRECTORY = "/usr/share/fonts/truetype/dejavu/"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def log(message):
    print(message, file=sys.stderr, flush=True)


def load_font(size, names=("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")):
    for name in names:
        path = FONT_DIRECTORY + name
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def parse_reset(iso_timestamp):
    if not iso_timestamp:
        return None
    return datetime.datetime.fromisoformat(iso_timestamp).astimezone()


def format_reset_current(reset_at):
    if reset_at is None:
        return "Reset: --"
    minutes = max(
        0, int((reset_at - datetime.datetime.now().astimezone()).total_seconds() // 60)
    )
    return f"Reset {reset_at:%H:%M} ({minutes // 60}h{minutes % 60:02d})"


def format_reset_weekly(reset_at):
    if reset_at is None:
        return "Reset: --"
    return f"Reset {WEEKDAYS[reset_at.weekday()]} {reset_at:%d.%m. %H:%M}"
