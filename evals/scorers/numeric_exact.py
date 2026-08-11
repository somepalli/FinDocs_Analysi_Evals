"""Numeric and normalized text answer matching."""

from __future__ import annotations

import re
import unicodedata

from evals.schema import AnswerExpectation

NUMBER_PATTERN = re.compile(r"[-+]?\(?\s*\d[\d,]*(?:\.\d+)?\s*\)?")


def parse_number(value: str) -> float | None:
    numbers = parse_numbers(value)
    return numbers[0] if numbers else None


def parse_numbers(value: str) -> tuple[float, ...]:
    numbers: list[float] = []
    for match in NUMBER_PATTERN.finditer(value):
        token = match.group(0).replace(",", "").replace(" ", "")
        negative = token.startswith("(") and token.endswith(")")
        token = token.strip("()")
        try:
            number = float(token)
        except ValueError:
            continue
        numbers.append(-number if negative else number)
    return tuple(numbers)


def normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def score_answer_value(predicted: str, expected: AnswerExpectation) -> bool:
    if expected.answer_type == "numeric":
        target = parse_number(expected.value)
        return target is not None and any(
            abs(actual - target) <= expected.tolerance for actual in parse_numbers(predicted)
        )
    return normalized_text(predicted) == normalized_text(expected.value)
