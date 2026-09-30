from solution import is_palindrome

def test_is_palindrome():
    # Typical cases
    assert is_palindrome("racecar") == True, "Should return True for a simple palindrome"
    assert is_palindrome("hello") == False, "Should return False for a non-palindrome"

    # Edge case: empty string
    assert is_palindrome("") == True, "An empty string should be considered a palindrome"

    # Edge case: single character
    assert is_palindrome("a") == True, "A single character should be considered a palindrome"
    assert is_palindrome("x") == True, "A single character should be considered a palindrome"

    # Edge case: punctuation
    assert is_palindrome("A man, a plan, a canal, Panama!") == True, "Should ignore punctuation, spaces, and case sensitivity"
    assert is_palindrome("Madam, I'm Adam.") == True, "Should ignore punctuation, spaces, and case sensitivity"
    assert is_palindrome("Was it a car or a cat I saw?") == True, "Should ignore punctuation, spaces, and case sensitivity"

    # Edge case: mixed case
    assert is_palindrome("RaceCar") == True, "Should work for mixed case palindromes"
    assert is_palindrome("NoOn") == True, "Should handle mixed case sensitivity"

    # Edge case: numbers and alphanumeric strings
    assert is_palindrome("12321") == True, "Should detect numeric palindromes"
    assert is_palindrome("abc12321cba") == True, "Should handle alphanumeric palindromes"
    assert is_palindrome("12345") == False, "Should return False for non-palindromic numbers"

    # Edge case: long string
    palindrome_long = "A" * 1000 + "B" + "A" * 1000
    non_palindrome_long = "A" * 1000 + "C" + "A" * 1000
    assert is_palindrome(palindrome_long) == False, "Should correctly identify a very long non-palindrome"
    assert is_palindrome(non_palindrome_long) == False, "Should correctly identify a very long non-palindrome"