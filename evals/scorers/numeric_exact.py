"""Numeric and normalized text answer matching."""

from __future__ import annotations

import re
import unicodedata

from evals.schema import AnswerExpectation

NUMBER_PATTERN = re.compile(r"[-+]?\(?\s*\d[\d,]*(?:\.\d+)?\s*\)?")


def parse_number(value: str) -> float | None:
    match = NUMBER_PATTERN.search(value)
    if match is None:
        return None
    token = match.group(0).replace(",", "").replace(" ", "")
    negative = token.startswith("(") and token.endswith(")")
    token = token.strip("()")
    try:
        number = float(token)
    except ValueError:
        return None
    return -number if negative else number


def normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def score_answer_value(predicted: str, expected: AnswerExpectation) -> bool:
    if expected.answer_type == "numeric":
        actual = parse_number(predicted)
        target = parse_number(expected.value)
        return (
            actual is not None and target is not None and abs(actual - target) <= expected.tolerance
        )
    return normalized_text(predicted) == normalized_text(expected.value)
