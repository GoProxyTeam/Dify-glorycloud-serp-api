"""GloryCloud goproxy search: fixed destinations and engine-specific inputs."""

import json
import math
from typing import Any

import httpx


API_BASE = "https://serpapi.glorycloud.com"
ENGINES = frozenset(("google_search", "google_image", "google_shopping", "google_news", "google_maps"))
SEARCH_FIELDS = frozenset(("location", "domain", "page", "domMap", "timeRange"))
MAP_FIELDS = frozenset(("country", "latitude", "longitude", "zoomLevel", "fetchLimit",
                        "minRating", "openNow", "includeDetails", "pageToken"))
PARAMETERS = SEARCH_FIELDS | MAP_FIELDS | {"engine", "query", "language", "maxResults", "format"}
TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
TIMEOUT_ADVICE = "The search may still finish and be billed. Do not retry immediately; check your usage before trying again."


class GloryCloudError(ValueError):
    """An actionable error without credentials or raw transport details."""


def validate_api_key(value: Any) -> str:
    """Check local format only; service access is checked when the tool runs."""
    if not isinstance(value, str) or not value.strip():
        raise GloryCloudError("Please enter your GloryCloud API Key, available at https://www.glorycloud.com/dashboard/settings/?link=1142bb.")
    key = value.strip()
    if not key.isascii() or any(ord(char) < 33 or ord(char) == 127 for char in key):
        raise GloryCloudError("The GloryCloud API Key contains invalid characters. Copy it again from your account.")
    return key


def _present(value: Any) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def _text(field: str, value: Any) -> str:
    if not isinstance(value, str):
        raise GloryCloudError(f"{field} must be a string.")
    return value.strip()


def _integer(field: str, value: Any, minimum: int, maximum: int | None = None) -> int:
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError
        number = int(value)
        if isinstance(value, float) and value != number:
            raise ValueError
        if number < minimum or (maximum is not None and number > maximum):
            raise ValueError
    except (ValueError, OverflowError):
        bound = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
        raise GloryCloudError(f"{field} must be a whole number {bound}.") from None
    return number


def _number(field: str, value: Any, minimum: float, maximum: float) -> float:
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError
        number = float(value)
        if not math.isfinite(number) or not minimum <= number <= maximum:
            raise ValueError
    except (ValueError, OverflowError):
        raise GloryCloudError(f"{field} must be a finite number between {minimum} and {maximum}.") from None
    return number


def _boolean(field: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    # The Dify SDK can serialize boolean form defaults as integer 0/1.
    if type(value) is int and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise GloryCloudError(f"{field} must be true or false.")


def _request(parameters: dict[str, Any]) -> tuple[str, bytes]:
    if set(parameters) - PARAMETERS:
        raise GloryCloudError("Unsupported or legacy search parameters. Reconfigure this tool node for version 0.0.1.")
    engine = parameters.get("engine", "google_search")
    if not isinstance(engine, str) or engine not in ENGINES:
        raise GloryCloudError("Choose a supported search type: web, images, shopping, news or maps.")
    query = parameters.get("query")
    if not isinstance(query, str) or not query.strip():
        raise GloryCloudError("query must be a non-empty search string.")
    try:
        query_size = len(query.encode("utf-8"))
    except UnicodeError:
        raise GloryCloudError("query must contain valid UTF-8 text.") from None
    if query_size > 2048:
        raise GloryCloudError("query must not exceed 2048 UTF-8 bytes.")
    payload: dict[str, Any] = {"query": query}
    if _present(parameters.get("language")):
        payload["language"] = _text("language", parameters["language"])
    if _present(parameters.get("maxResults")):
        payload["maxResults"] = _integer("maxResults", parameters["maxResults"], 0, 40 if engine == "google_maps" else 100)

    options: dict[str, Any] = {}
    if _present(parameters.get("format")):
        formats = {"json": ["json"], "html": ["html"], "json+html": ["json", "html"]}
        selected = _text("format", parameters["format"]).lower()
        if selected not in formats:
            raise GloryCloudError("format must be json, html or json+html.")
        options["format"] = formats[selected]

    # Dify keeps form values when users switch search type. Only process active fields.
    if engine == "google_maps":
        if _present(parameters.get("country")):
            country = _text("country", parameters["country"])
            if len(country) != 2 or not country.isascii() or not country.isalpha():
                raise GloryCloudError("country must be a two-letter country code, for example us.")
            payload["country"] = country.lower()
        has_latitude = _present(parameters.get("latitude"))
        has_longitude = _present(parameters.get("longitude"))
        if has_latitude != has_longitude:
            raise GloryCloudError("For maps, provide both latitude and longitude, or leave both empty.")
        if has_latitude:
            options["latitude"] = _number("latitude", parameters["latitude"], -90, 90)
            options["longitude"] = _number("longitude", parameters["longitude"], -180, 180)
        for field, lower, upper in (("zoomLevel", 0, 21), ("fetchLimit", 1, 40)):
            if _present(parameters.get(field)):
                options[field] = _integer(field, parameters[field], lower, upper)
        if _present(parameters.get("minRating")):
            options["minRating"] = _number("minRating", parameters["minRating"], 0, 5)
        for field in ("openNow", "includeDetails"):
            if _present(parameters.get(field)):
                options[field] = _boolean(field, parameters[field])
        if _present(parameters.get("pageToken")):
            options["pageToken"] = _text("pageToken", parameters["pageToken"])
    else:
        for field in ("location", "domain"):
            if _present(parameters.get(field)):
                options[field] = _text(field, parameters[field])
        if _present(parameters.get("page")):
            options["page"] = _integer("page", parameters["page"], 1)
        if _present(parameters.get("domMap")):
            options["domMap"] = _boolean("domMap", parameters["domMap"])
        if engine == "google_news" and _present(parameters.get("timeRange")):
            time_range = _text("timeRange", parameters["timeRange"])
            if time_range not in ("1h", "1d", "7d", "1m", "1y"):
                raise GloryCloudError("timeRange must be 1h, 1d, 7d, 1m or 1y.")
            options["timeRange"] = time_range
    if options:
        payload["options"] = options
    try:
        content = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (ValueError, UnicodeError):
        raise GloryCloudError("Search parameters must contain valid JSON and UTF-8 values.") from None
    if len(content) > 64 * 1024:
        raise GloryCloudError("Search parameters exceed the 64 KiB request limit. Shorten optional text values.")
    return engine, content


def _safe_text(value: Any, key: str, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    text = value.replace(key, "[REDACTED]")
    return " ".join("".join(char if char.isprintable() else " " for char in text).split())[:limit]


def _service_error(status: int, result: Any, key: str) -> GloryCloudError:
    result = result if isinstance(result, dict) else {}
    code = result.get("code")
    valid_code = type(code) is int
    label = f"HTTP {status}" + (f", code {code}" if valid_code else "")
    detail = _safe_text(result.get("msg"), key, 500)
    data = result.get("data")
    request_id = _safe_text(data.get("requestId"), key, 80) if isinstance(data, dict) else ""
    if code == 1517 or status == 504:
        advice = TIMEOUT_ADVICE
    elif code == 1509:
        advice = "The result is too large to deliver; this search may have been billed. Reduce the requested result size."
    elif code == 1502 or status == 401:
        advice = "Check your API Key and account access."
    elif code == 1507 or status == 429:
        advice = "The rate limit was reached. Wait before trying again."
    else:
        advice = "Check your account, available quota and search parameters."
    suffix = f" Request ID: {request_id}." if request_id else ""
    return GloryCloudError(f"GloryCloud request failed ({label}). {detail + '. ' if detail else ''}{advice}{suffix}")


def search(api_key: Any, parameters: dict[str, Any]) -> dict[str, Any]:
    """Make one goproxy search and preserve the complete successful JSON envelope."""
    key = validate_api_key(api_key)
    engine, content = _request(parameters)
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
            response = client.post(f"{API_BASE}/api/serp/{engine}",
                                   headers={"X-Api-Key": key, "Content-Type": "application/json"},
                                   content=content)
    except httpx.TimeoutException:
        raise GloryCloudError("The GloryCloud request timed out. " + TIMEOUT_ADVICE) from None
    except httpx.RequestError:
        raise GloryCloudError("Could not connect to GloryCloud. Check connectivity and your usage before trying again.") from None

    status = response.status_code
    try:
        result = response.json()
    except ValueError:
        if not 200 <= status < 300:
            raise _service_error(status, None, key) from None
        raise GloryCloudError("GloryCloud returned an invalid JSON response.") from None
    if not 200 <= status < 300:
        raise _service_error(status, result, key)
    if not isinstance(result, dict) or type(result.get("code")) is not int:
        raise GloryCloudError("GloryCloud returned an unexpected response format.")
    if result["code"] != 0:
        raise _service_error(status, result, key)
    data = result.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("result"), dict):
        raise GloryCloudError("GloryCloud returned an unexpected search result format.")
    count = data.get("resultCount")
    if (not isinstance(data.get("requestId"), str) or not data["requestId"].strip()
            or data.get("engine") != engine or "resultCount" not in data
            or (count is not None and (type(count) is not int or count < 0))):
        raise GloryCloudError("GloryCloud returned incomplete or inconsistent search metadata.")
    return result
