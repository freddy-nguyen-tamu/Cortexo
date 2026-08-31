"""Hidden tests for synthetic-bugfix task synthetic-bugfix/range_util."""

from range_util import clamp, chunk


def test_clamp_inside():
    assert clamp(2, 0, 3) == 2


def test_clamp_above_high():
    assert clamp(5, 0, 3) == 3


def test_clamp_below_low():
    assert clamp(-1, 0, 3) == 0


def test_clamp_edges():
    assert clamp(0, 0, 3) == 0
    assert clamp(3, 0, 3) == 3


def test_chunk_even():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunk_odd_tail():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_size_zero():
    assert chunk([1, 2], 0) == []


def test_chunk_bigger_than_list():
    assert chunk([1, 2], 5) == [[1, 2]]