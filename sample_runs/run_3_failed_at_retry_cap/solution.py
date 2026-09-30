def is_palindrome(text: str) -> bool:
    processed = ''.join(ch.lower() for ch in text if ch.isalnum())
    return processed == processed[::-1]