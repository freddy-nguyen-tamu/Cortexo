"""range_util - buggy variant used by the synthetic-bugfix suite.

Seeded bugs (see tasks/synthetic-bugfix.json for the verified correct patch):

1. comparison-reversal + swapped operand in `clamp`:
   - clamp(5, 0, 3) returns 0 but must return 3
   - clamp(-1, 0, 3) returns 3 but must return 0

2. off-by-one slice in `chunk`:
   - chunk([1,2,3,4,5], 2) returns [[1,2]] but must return [[1,2],[3,4],[5]]
"""


def clamp(value, low, high):
    if value < low:
        return high
    if value > high:
        return low
    return value


def chunk(items, size):
    if size <= 0:
        return []
    out = []
    for i in range(0, len(items), size):
        out.append(items[i:i + size])
    return out[:size]