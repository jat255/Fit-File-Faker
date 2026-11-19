# milliseconds from Unix epoch (start of 1970) to Sun Dec 31 00:00:00 1989
MILLISECONDS_EPOCH_1989_DELTA = 631065600000


def to_seconds_since_1989_epoch(milliseconds_since_epoch: int) -> int:
    seconds_since_1989_epoch = (milliseconds_since_epoch - MILLISECONDS_EPOCH_1989_DELTA) // 1000
    return seconds_since_1989_epoch


def to_milliseconds_since_epoch(seconds_since_1989_epoch: int) -> int:
    milliseconds_since_epoch = seconds_since_1989_epoch * 1000 + MILLISECONDS_EPOCH_1989_DELTA
    return milliseconds_since_epoch


def to_semicircles(degrees: int) -> int:
    return round(2147483648 * degrees / 180.0)


def to_degrees(semicircles: int) -> float:
    return (semicircles * 180.0) / 2147483648
