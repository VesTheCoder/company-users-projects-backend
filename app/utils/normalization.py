import unicodedata


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def normalize_identifier(value: str) -> str:
    return normalize_text(value).casefold()
