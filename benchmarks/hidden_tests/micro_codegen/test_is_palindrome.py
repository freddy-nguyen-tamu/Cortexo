"""Hidden tests for micro-codegen task micro-codegen/is_palindrome."""

from solution import is_palindrome


def test_plain_palindrome():
    assert is_palindrome("racecar") is True


def test_case_insensitive():
    assert is_palindrome("RaceCar") is True


def test_ignores_punctuation_and_spaces():
    assert is_palindrome("A man, a plan, a canal: Panama") is True


def test_includes_digits():
    assert is_palindrome("12321") is True


def test_rejects_different_sequences():
    assert is_palindrome("race a car") is False


def test_empty_is_palindrome():
    assert is_palindrome("") is True