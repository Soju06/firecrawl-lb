from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import ceil
from typing import Any, cast

JsonObject = Mapping[str, Any]

_EXPENSIVE_SCRAPE_FORMATS = frozenset(
    {
        "json",
        "summary",
        "screenshot",
        "audio",
        "video",
        "question",
        "highlights",
    }
)


def estimate_credits(endpoint: str, payload: JsonObject, response_json: JsonObject | None = None) -> int:
    response_credits = _response_credits_used(response_json)
    if response_credits is not None:
        return response_credits

    if endpoint == "scrape":
        return _estimate_scrape_credits(payload)
    if endpoint == "map":
        return 1
    if endpoint == "search":
        return _estimate_search_credits(payload)
    if endpoint == "crawl":
        return max(1, _int_value(payload.get("limit"), default=1))
    if endpoint == "batch_scrape":
        urls = payload.get("urls")
        return max(1, len(urls) if isinstance(urls, Sequence) and not isinstance(urls, str) else 0)
    return 1


def _response_credits_used(response_json: JsonObject | None) -> int | None:
    if response_json is None:
        return None

    top_level_credits = response_json.get("creditsUsed")
    if _is_plain_int(top_level_credits):
        return top_level_credits

    data = response_json.get("data")
    if isinstance(data, Mapping):
        nested_credits = data.get("creditsUsed")
        if _is_plain_int(nested_credits):
            return nested_credits

    return None


def _estimate_scrape_credits(payload: JsonObject) -> int:
    formats = payload.get("formats")
    normalized_formats = _normalized_scrape_formats(formats)

    credits = 1
    credits += len(normalized_formats & _EXPENSIVE_SCRAPE_FORMATS)
    if payload.get("onlyCleanContent"):
        credits += 1
    if payload.get("actions"):
        credits += 1
    return credits


def _estimate_search_credits(payload: JsonObject) -> int:
    limit = max(1, _int_value(payload.get("limit"), default=10))
    sources = payload.get("sources")
    source_count = len(sources) if isinstance(sources, Sequence) and not isinstance(sources, str) else 1
    source_count = max(1, source_count)

    credits = 2 * ceil(limit / 10) * source_count
    scrape_options = payload.get("scrapeOptions")
    if isinstance(scrape_options, Mapping):
        credits += _estimate_search_scrape_reservation(
            limit=limit,
            source_count=source_count,
            scrape_options=scrape_options,
        )
    return credits


def _estimate_search_scrape_reservation(
    *,
    limit: int,
    source_count: int,
    scrape_options: JsonObject,
) -> int:
    del source_count
    return limit * _estimate_scrape_credits(scrape_options)


def _normalized_scrape_formats(formats: object) -> set[str]:
    if not isinstance(formats, Sequence) or isinstance(formats, str):
        return {"markdown"}

    normalized: set[str] = set()
    for item in formats:
        if isinstance(item, str):
            normalized.add(item)
        elif isinstance(item, Mapping):
            item_mapping = cast(Mapping[str, Any], item)
            format_type = item_mapping.get("type")
            if isinstance(format_type, str):
                normalized.add(format_type)
    return normalized or {"markdown"}


def _int_value(value: object, *, default: int) -> int:
    if _is_plain_int(value):
        return cast(int, value)
    if isinstance(value, str):
        return int(value)
    return default


def _is_plain_int(value: object) -> bool:
    return type(value) is int
