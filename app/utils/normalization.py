import unicodedata


def normalize_text(value):
    return (
        unicodedata.normalize("NFKC", value).strip()
        if isinstance(value, str)
        else value
    )


def normalize_identifier(value: str) -> str:
    return normalize_text(value).casefold()
