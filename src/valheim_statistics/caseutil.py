import re


def pascal_to_words(text: str) -> str:
    text = re.sub("(.)([A-Z][a-z]+)", r"\1 \2", text)
    text = re.sub("([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s*_\s*", r" ", text)
    return text.title()


def pascal_to_snake(text: str) -> str:
    text = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    text = re.sub("([a-z0-9])([A-Z])", r"\1_\2", text)
    return text.lower()
