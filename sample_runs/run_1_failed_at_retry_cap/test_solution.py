from solution import is_palindrome

def test_is_palindrome():
    # Edge case: Empty string
    assert is_palindrome("") == True, "Empty string should be palindrome"

    # Edge case: Single character
    assert is_palindrome("a") == True, "Single character should be palindrome"
    assert is_palindrome("Z") == True, "Single character should be palindrome"

    # Typical cases: Simple palindromes
    assert is_palindrome("madam") == True, "'madam' should be palindrome"
    assert is_palindrome("racecar") == True, "'racecar' should be palindrome"

    # Typical case: Not a palindrome
    assert is_palindrome("hello") == False, "'hello' should not be palindrome"

    # Edge case: Palindrome with punctuation and spaces
    assert is_palindrome("A man, a plan, a canal, Panama!") == True, \
        "'A man, a plan, a canal, Panama!' should be a palindrome"

    # Edge case: Mixed case palindrome
    assert is_palindrome("Able was I, I saw Elba") == True, \
        "'Able was I, I saw Elba' should be a palindrome"

    # Edge case: String with only punctuation and spaces
    assert is_palindrome("!!! !!!") == True, "'!!! !!!' should be palindrome"

    # Edge case: Long palindrome
    long_palindrome = "a" * 10000 + "b" + "a" * 10000
    assert is_palindrome(long_palindrome) == False, "Long string with one non-matching character should not be palindrome"

    # Edge case: Very long palindrome
    very_long_palindrome = "a" * 10000
    assert is_palindrome(very_long_palindrome) == True, "Long string with all matching characters should be palindrome"

if __name__ == "__main__":
    test_is_palindrome()
    print("All tests passed!")