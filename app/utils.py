import re

ARABIC_PATTERN = re.compile(r'[\u0600-\u06FF]')

def detect_languages(text):

    tags = []

    words = text.split()

    for word in words:

        if ARABIC_PATTERN.search(word):
            lang = "AR"

        elif any(c in word.lower() for c in ["flight", "book", "schedule", "transport"]):
            lang = "EN"

        else:
            lang = "ID"

        tags.append((word, lang))

    return tags


def normalize_text(text):

    text = text.strip()

    text = text.replace("  ", " ")

    # Spelling overrides whisper phonetic mistakes
    replacements = {
        r'(?i)\bh?uridu\b': 'uridu',
        r'(?i)\bbuk flaik\b': 'book flight',
        r'(?i)\bbuk\s+flight\b': 'book flight',
        r'(?i)\bskedul\b': 'schedule',
        r'(?i)\badalah schedule\b': 'afdhal schedule',
        r'(?i)\bafdal skedul\b': 'afdhal schedule',
        r'(?i)\bafdal\b': 'afdhal',
        r'(?i)\bajidah\b': 'ajida',
        r'(?i)\bmubashiroh\b': 'mubashirah',
        r'(?i)\brihlatan\b': 'rihlatan',
        r'(?i)\bminje dah\b': 'min jeddah',
        r'(?i)\bilama dina gwadan\b': 'ila madinah ghadan',
        r'(?i)\btransport\b': 'transport',
        r'(?i)\bfisik\b': 'visit',
        r'(?i)\bumroh\b': 'umrah'
    }

    for pattern, rep in replacements.items():
        text = re.sub(pattern, rep, text)

    return text

    return text