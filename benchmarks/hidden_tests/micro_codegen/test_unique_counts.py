"""Hidden tests for micro-codegen task micro-codegen/unique_counts."""

from solution import unique_counts


def test_counts_preserve_order():
    assert unique_counts([3, 1, 1, 2, 3]) == {3: 2, 1: 2, 2: 1}


def test_unique_values():
    assert unique_counts(["a", "b", "c"]) == {"a": 1, "b": 1, "c": 1}


def test_empty_input():
    assert unique_counts([]) == {}


def test_mixed_types():
    assert unique_counts([1, "1", 1]) == {1: 2, "1": 1}