"""UTC ISO-8601 <-> Unix seconds using integer calendar maths.

time.mktime() is avoided because its epoch differs between MicroPython ports.
"""

# Device clocks before an NTP sync hold a fixed past date (rp2: 2021, esp32: 2000).
MIN_SYNCED_YEAR = 2024


def _days_from_civil(year, month, day):
    if month <= 2:
        year -= 1
    era = (year if year >= 0 else year - 399) // 400
    year_of_era = year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468


def _civil_from_days(days):
    days += 719468
    era = (days if days >= 0 else days - 146096) // 146097
    day_of_era = days - era * 146097
    year_of_era = (day_of_era - day_of_era // 1460 + day_of_era // 36524 - day_of_era // 146096) // 365
    year = year_of_era + era * 400
    day_of_year = day_of_era - (365 * year_of_era + year_of_era // 4 - year_of_era // 100)
    shifted_month = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * shifted_month + 2) // 5 + 1
    month = shifted_month + (3 if shifted_month < 10 else -9)
    if month <= 2:
        year += 1
    return year, month, day


def datetime_to_epoch(parts):
    """(year, month, day, hour, minute, second, ...) in UTC to Unix seconds."""
    year, month, day, hour, minute, second = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
    return _days_from_civil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second


def epoch_to_datetime(seconds):
    """Unix seconds to (year, month, day, hour, minute, second, weekday) in UTC; Monday is 0."""
    seconds = int(seconds)
    days = seconds // 86400
    remainder = seconds - days * 86400
    year, month, day = _civil_from_days(days)
    # 1970-01-01 was a Thursday (weekday 3).
    return (year, month, day, remainder // 3600, (remainder % 3600) // 60, remainder % 60, (days + 3) % 7)


def iso_to_epoch(value):
    """Parse 'YYYY-MM-DDTHH:MM:SSZ' to Unix seconds, or None if malformed."""
    if not isinstance(value, str) or len(value) < 19:
        return None
    try:
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        second = int(value[17:19])
    except ValueError:
        return None
    return _days_from_civil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second


def epoch_to_iso(seconds):
    seconds = int(seconds)
    days = seconds // 86400
    remainder = seconds - days * 86400
    year, month, day = _civil_from_days(days)
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
        year, month, day, remainder // 3600, (remainder % 3600) // 60, remainder % 60,
    )
