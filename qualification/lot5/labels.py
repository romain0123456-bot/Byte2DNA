"""Label normalization for the isolated LOT5 qualification."""


def normalize_label(value):
    """Lowercase a string and join its whitespace-separated words with hyphens."""
    if not isinstance(value, str):
        raise TypeError("label must be a string")
    return "-".join(value.lower().split())
