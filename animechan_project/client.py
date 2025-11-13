"""
Animechan API client implementation.

Provides a basic GET wrapper, in-memory caching (TTL), exponential backoff retries,
rate-limit sleep between requests, and convenience methods for common endpoints.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import requests


logger = logging.getLogger(__name__)


class AnimechanError(RuntimeError):
    """Animechan API invocation error."""


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class AnimechanClient:
    """Synchronous client for communicating with the Animechan API.

    Attributes:
        base_url: Base URL of the API, customizable for testing.
        timeout: Per-request HTTP timeout in seconds.
        max_retries: Number of retries after a failure.
        backoff_factor: Base factor for exponential backoff; next sleep is
            backoff_factor * (2 ** attempt).
        cache_ttl: Cache time-to-live in seconds; 0 or None disables caching.
        rate_limit_sleep: Optional sleep after each request to avoid rate limits.
    """

    DEFAULT_BASE_URL = "https://api.animechan.io/v1"

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        cache_ttl: Optional[float] = 300.0,
        rate_limit_sleep: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.cache_ttl = cache_ttl
        self.rate_limit_sleep = rate_limit_sleep
        self._cache: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], _CacheEntry] = {}
        self._cache_lock = threading.Lock()

    # --------------------------------------------------------------------- #
    # Public methods
    # --------------------------------------------------------------------- #
    def get_random_quote(self) -> Dict[str, Any]:
        """Fetch a random anime quote."""
        return self._get("/quotes/random")

    def get_quotes_by_character(self, character: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch quotes by character name."""
        params: Dict[str, Any] = {"character": character}
        if limit is not None:
            params["limit"] = limit
        data = self._get("/quotes", params=params)
        return self._ensure_list(data)

    def get_quotes_by_show(self, show: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch quotes by anime title."""
        params: Dict[str, Any] = {"title": show}
        if limit is not None:
            params["limit"] = limit
        data = self._get("/quotes", params=params)
        return self._ensure_list(data)

    def get_all_quotes(self, *, page: int = 1) -> Dict[str, Any]:
        """Fetch all quotes with pagination; response contains the `data` field."""
        params = {"page": page}
        return self._get("/quotes", params=params)

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        with self._cache_lock:
            self._cache.clear()

    # --------------------------------------------------------------------- #
    # Internal implementation
    # --------------------------------------------------------------------- #
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        cache_key = self._build_cache_key(method, url, params)
        if self.cache_ttl and method.upper() == "GET":
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = self._parse_response(response)
                if self.cache_ttl and method.upper() == "GET":
                    self._write_cache(cache_key, data)
                if self.rate_limit_sleep > 0:
                    time.sleep(self.rate_limit_sleep)
                return data
            except requests.RequestException as exc:  # pragma: no cover - requests specific
                last_exc = exc
                self._handle_retry(exc, attempt)

        message = f"Failed to call Animechan API: {last_exc}"
        raise AnimechanError(message) from last_exc

    def _handle_retry(self, exc: Exception, attempt: int) -> None:
        if attempt >= self.max_retries:
            return
        sleep_time = self.backoff_factor * (2 ** attempt)
        logger.warning("Animechan request failed (%s). Retrying in %.2fs", exc, sleep_time)
        time.sleep(sleep_time)

    def _parse_response(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise AnimechanError("Response is not valid JSON") from exc

    # ------------------------------------------------------------------ #
    # Caching
    # ------------------------------------------------------------------ #
    def _build_cache_key(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
    ) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        normalized_params: Tuple[Tuple[str, str], ...] = tuple(
            sorted((str(k), self._serialize_param(v)) for k, v in (params or {}).items())
        )
        return method.upper(), ((url, ""),) + normalized_params

    def _serialize_param(self, value: Any) -> str:
        if isinstance(value, (list, tuple, set)):
            return ",".join(map(str, value))
        return str(value)

    def _read_cache(self, key: Tuple[str, Tuple[Tuple[str, str], ...]]) -> Optional[Any]:
        now = time.time()
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry and entry.expires_at > now:
                logger.debug("Cache hit for %s", key)
                return entry.value
            if entry:
                logger.debug("Cache expired for %s", key)
                self._cache.pop(key, None)
        return None

    def _write_cache(self, key: Tuple[str, Tuple[Tuple[str, str], ...]], value: Any) -> None:
        with self._cache_lock:
            self._cache[key] = _CacheEntry(value=value, expires_at=time.time() + (self.cache_ttl or 0))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _ensure_list(self, data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            content = data.get("data")
            if isinstance(content, list):
                return content
        raise AnimechanError("Unexpected response format for list endpoint")


def bulk_fetch_quotes(
    client: AnimechanClient,
    *,
    characters: Optional[Iterable[str]] = None,
    shows: Optional[Iterable[str]] = None,
    per_request_limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch quotes for multiple characters/anime to facilitate data collection.

    Args:
        client: Instance of AnimechanClient.
        characters: Iterable of character names to query.
        shows: Iterable of anime titles to query.
        per_request_limit: Optional per-request limit if supported by API.

    Returns:
        List[Dict[str, Any]]: Aggregated list of quotes.
    """

    collected: List[Dict[str, Any]] = []
    if characters:
        for character in characters:
            try:
                collected.extend(client.get_quotes_by_character(character, limit=per_request_limit))
            except AnimechanError as exc:  # pragma: no cover - when network is unavailable, just log
                logger.error("Failed to fetch quotes for character %s: %s", character, exc)
    if shows:
        for show in shows:
            try:
                collected.extend(client.get_quotes_by_show(show, limit=per_request_limit))
            except AnimechanError as exc:  # pragma: no cover
                logger.error("Failed to fetch quotes for show %s: %s", show, exc)
    return collected


