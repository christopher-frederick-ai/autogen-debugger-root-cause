def is_palindrome(text: str) -> bool:
    filtered_text = ''.join(char.lower() for char in text if char.isalnum())
    return filtered_text == filtered_text[::-1]