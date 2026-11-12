import time


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# Some MicroPython ports count seconds from 2000 instead of 1970.
EPOCH_OFFSET = 0 if time.gmtime(0)[0] == 1970 else 946_684_800


def log(message):
    print(message)


def unix_time():
    """Seconds since 1970 in UTC, as used by the expiresAt value of the credentials."""
    return time.time() + EPOCH_OFFSET


def parse_reset(iso_timestamp):
    """Turn "2025-10-29T09:00:00.123456+00:00" into seconds (UTC, same epoch as time.time())."""
    if not iso_timestamp:
        return None
    date, clock = iso_timestamp.split("T")
    year, month, day = (int(part) for part in date.split("-"))
    seconds = time.mktime(
        (year, month, day, int(clock[0:2]), int(clock[3:5]), int(clock[6:8]), 0, 0)
    )
    zone = clock[8:]
    sign_position = max(zone.find("+"), zone.find("-"))
    if sign_position >= 0:
        sign = -1 if zone[sign_position] == "-" else 1
        hours = int(zone[sign_position + 1 : sign_position + 3])
        minutes = int(zone[sign_position + 4 : sign_position + 6])
        seconds -= sign * (hours * 3600 + minutes * 60)
    return seconds


def sunday_of_month(year, month, week):
    """Day of the month of the given Sunday: week 1 is the first, -1 the last."""
    if week > 0:
        first_weekday = time.gmtime(time.mktime((year, month, 1, 0, 0, 0, 0, 0)))[6]
        return 1 + (6 - first_weekday) % 7 + 7 * (week - 1)
    next_month = time.mktime((year + month // 12, month % 12 + 1, 1, 0, 0, 0, 0, 0))
    last_day = time.gmtime(next_month - 86400)
    return last_day[2] - (last_day[6] + 1) % 7


class Timezone:
    """The ESP32 has no timezone database, so the offset and summer time rule are set here."""

    def __init__(self, utc_offset=0, dst=None):
        if dst not in (None, "eu", "us"):
            raise ValueError("dst must be None, 'eu' or 'us'")
        self.utc_offset = int(utc_offset * 3600)
        self.dst = dst

    def localtime(self, seconds):
        return time.gmtime(seconds + self.offset(seconds))

    def offset(self, seconds):
        if self.dst and self.is_summer_time(seconds):
            return self.utc_offset + 3600
        return self.utc_offset

    def is_summer_time(self, seconds):
        year = time.gmtime(seconds)[0]
        if self.dst == "eu":
            # Last Sunday in March to last Sunday in October, 01:00 UTC.
            start = time.mktime((year, 3, sunday_of_month(year, 3, -1), 1, 0, 0, 0, 0))
            end = time.mktime((year, 10, sunday_of_month(year, 10, -1), 1, 0, 0, 0, 0))
        else:
            # Second Sunday in March, 02:00 local, to first Sunday in November, 02:00 local.
            start = time.mktime((year, 3, sunday_of_month(year, 3, 2), 2, 0, 0, 0, 0))
            end = time.mktime((year, 11, sunday_of_month(year, 11, 1), 1, 0, 0, 0, 0))
            start, end = start - self.utc_offset, end - self.utc_offset
        return start <= seconds < end


def format_reset_current(reset_at, timezone):
    if reset_at is None:
        return "Reset: --"
    local = timezone.localtime(reset_at)
    minutes = max(0, int(reset_at - time.time()) // 60)
    return f"Reset {local[3]:02d}:{local[4]:02d} ({minutes // 60}h{minutes % 60:02d})"


def format_reset_weekly(reset_at, timezone):
    if reset_at is None:
        return "Reset: --"
    local = timezone.localtime(reset_at)
    weekday, day, month = WEEKDAYS[local[6]], local[2], local[1]
    return f"Reset {weekday} {day:02d}.{month:02d}. {local[3]:02d}:{local[4]:02d}"
