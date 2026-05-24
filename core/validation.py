# ============================================================
# Griffin Library - Query Validation
# ============================================================
# Validates search queries against natural language patterns.
# Rejects numbers-only, low-alpha, keyboard mash, and repetition.
# ============================================================

import re
from typing import Tuple


# Common short words that should always pass
_COMMON_SHORT = {"i", "a", "go", "on", "up", "no", "ok", "so", "us", "we"}


def is_meaningful_query(query: str) -> Tuple[bool, str]:
    """Validate that a search query looks like a real natural-language input.

    Returns (is_valid, reason_code). Reason codes are stable identifiers
    used by the UI for error messages.

    Reasons: too_short | numbers_only | low_alpha | no_words |
             keyboard_mash | repetition
    """
    q = (query or "").strip()

    if len(q) < 3:
        return False, "too_short"

    # Pure numbers (digits + whitespace + light punctuation around digits)
    if re.fullmatch(r"[\d\s\.,\-_/\\]+", q) and any(c.isdigit() for c in q):
        return False, "numbers_only"

    # Need a healthy ratio of letters
    alpha_chars = sum(c.isalpha() for c in q)
    if alpha_chars / len(q) < 0.5:
        return False, "low_alpha"

    # Need at least one tokenizable word
    tokens = re.findall(r"[a-zA-Z]{2,}", q)
    if not tokens:
        return False, "no_words"

    # Repetition: same character 5+ times in a row
    if re.search(r"(.)\1{4,}", q):
        return False, "repetition"

    # Keyboard mash detection (FIXED regex)
    # Old bug: r"[^aeiouAEIOU\s\d\W]{6,}" rejected "strengths", "rhythms"
    # New approach: token suspicious if it has zero vowels (incl. y) and length >= 4.
    # Real English has very few such words (mostly abbreviations / interjections),
    # so multiple vowel-less tokens in one query is a strong mash signal.
    suspicious = 0
    for tok in tokens:
        tl = tok.lower()
        if len(tl) >= 4 and not re.search(r"[aeiouy]", tl):
            suspicious += 1

    # If MOST tokens lack vowels, it's mash
    if suspicious >= 2 or (suspicious >= 1 and suspicious / len(tokens) >= 0.5):
        return False, "keyboard_mash"

    # Adjacent-key mash: 2+ tokens of length 1-3 made of just home-row keys
    home_row = set("asdfghjkl")
    junk_tokens = sum(
        1 for t in tokens
        if len(t) <= 4 and all(c.lower() in home_row for c in t)
        and not re.search(r"[aeiouy]", t.lower())
    )
    if junk_tokens >= 2:
        return False, "keyboard_mash"

    return True, ""


def humanize_error(reason: str, name: str = "") -> str:
    """Convert a reason code to a friendly UI message."""
    n = name or "friend"
    messages = {
        "too_short": f"A few more words would help me understand, {n} 🌿",
        "numbers_only": f"Try describing a mood or theme instead of numbers 📖",
        "low_alpha": f"That looks mostly like symbols - try real words 🌱",
        "no_words": f"I need at least one word to search, {n}",
        "keyboard_mash": f"That looks like random typing 🤔 Try again.",
        "repetition": f"Too many repeated characters - try a real phrase",
        "empty_query": f"Tell me what you're looking for 🌿",
        "no_match": f"I couldn't find anything matching that, {n}. Try a different mood or theme.",
        "internal_error": f"Something went wrong. Please try again.",
    }
    return messages.get(reason, f"That doesn't look like a book description, {n}.")
