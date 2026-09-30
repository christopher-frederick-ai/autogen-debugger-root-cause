from solution import is_palindrome

def test_is_palindrome():
    # Typical cases
    assert is_palindrome("racecar") == True, "racecar should be a palindrome"
    assert is_palindrome("hello") == False, "hello should not be a palindrome"
    assert is_palindrome("madam") == True, "madam should be a palindrome"

    # Edge cases: empty string
    assert is_palindrome("") == True, "Empty string should be considered a palindrome"

    # Edge cases: punctuation
    assert is_palindrome("A man, a plan, a canal, Panama") == True, "Should handle punctuation and spaces"
    assert is_palindrome("No lemon, no melon") == True, "Should handle punctuation and spaces"

    # Edge cases: mixed case
    assert is_palindrome("RaceCar") == True, "Should handle mixed case correctly"
    assert is_palindrome("MadAm") == True, "Should handle mixed case correctly"

    # Edge cases: spaces
    assert is_palindrome("nurses run") == True, "Should handle spaces"

    # Edge cases: long string
    long_palindrome = "A" * 1000000 + "B" + "A" * 1000000
    assert is_palindrome(long_palindrome) == False, "Large string that is not a palindrome"
    very_long_palindrome = "A" * 1000000 + "A" * 1000000
    assert is_palindrome(very_long_palindrome) == True, "Very long string that is a palindrome"

    print("All test cases passed.")

if __name__ == "__main__":
    test_is_palindrome()