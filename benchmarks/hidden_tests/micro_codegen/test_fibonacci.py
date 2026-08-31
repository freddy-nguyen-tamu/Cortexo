"""Hidden tests for micro-codegen task micro-codegen/fibonacci."""

from solution import fibonacci


def test_fibonacci_zero():
    assert fibonacci(0) == []


def test_fibonacci_one():
    assert fibonacci(1) == [0, 1]


def test_fibonacci_ten():
    assert fibonacci(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]


def test_fibonacci_negative():
    assert fibonacci(-1) == []