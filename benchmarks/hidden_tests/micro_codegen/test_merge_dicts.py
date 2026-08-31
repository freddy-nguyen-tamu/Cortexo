"""Hidden tests for micro-codegen task micro-codegen/merge_dicts."""

from solution import merge_dicts


def test_merge_disjoint():
    assert merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_overwrite():
    assert merge_dicts({"a": 1, "b": 1}, {"b": 2, "c": 3}) == {"a": 1, "b": 2, "c": 3}


def test_merge_empty_left():
    assert merge_dicts({}, {"x": 1}) == {"x": 1}


def test_merge_does_not_mutate_inputs():
    left = {"a": 1}
    right = {"b": 2}
    result = merge_dicts(left, right)
    assert left == {"a": 1}
    assert right == {"b": 2}
    assert result == {"a": 1, "b": 2}