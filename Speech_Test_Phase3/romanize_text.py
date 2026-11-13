"""Offline, readable Roman-letter rendering; recognition text stays unchanged."""
from functools import lru_cache
import re
import unicodedata

_romanizer = None


@lru_cache(maxsize=2048)
def romanize(text, language):
    global _romanizer
    # Avoid loading language tables for English or already Romanized recognition.
    if any('\u0900' <= c <= '\u097f' or '\u0980' <= c <= '\u09ff' for c in text):
        if _romanizer is None:
            from uroman import Uroman
            _romanizer = Uroman()
        text = _romanizer.romanize_string(text, lcode={'hi': 'hin', 'bn': 'ben'}.get(language))
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    if language == 'hi':
        # Common Hindi nasal vowels in familiar Hinglish spelling.
        for before, after in {'maim': 'main', 'haim': 'hain', 'huum': 'hoon', 'himdii': 'hindi'}.items():
            text = re.sub(r'\b' + before + r'\b', after, text, flags=re.IGNORECASE)
    return text
