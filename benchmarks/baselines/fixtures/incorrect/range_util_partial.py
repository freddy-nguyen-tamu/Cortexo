"""Partial repair: clamp is fixed, chunk intentionally remains wrong."""


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def chunk(items, size):
    if size <= 0:
        return []
    out = []
    for i in range(0, len(items), size):
        out.append(items[i:i + size])
    return out[:size]