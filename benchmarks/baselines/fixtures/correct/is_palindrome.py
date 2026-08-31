def is_palindrome(s: str) -> bool:
    normalized = "".join(ch.lower() for ch in s if ch.isalnum())
    return normalized == normalized[::-1]