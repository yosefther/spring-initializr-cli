"""HTTP client for start.spring.io."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://start.spring.io"
USER_AGENT = "spring-initializr-cli/1.1"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 0.75
DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60


class SpringInitializrClient:
    """Small client responsible for all remote calls."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        user_agent: str = USER_AGENT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        use_cache: bool = True,
        refresh_metadata: bool = False,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        cache_path: Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.use_cache = use_cache
        self.refresh_metadata = refresh_metadata
        self.cache_ttl_seconds = max(0, cache_ttl_seconds)
        self.max_retries = max(0, max_retries)
        self.backoff_seconds = max(0.0, backoff_seconds)
        self.cache_path = cache_path or _default_cache_path()

        self._metadata_url: str | None = None
        self._starter_url: str | None = None
        self._discovered_endpoints: dict[str, str] | None = None
        self.last_metadata_source = "none"

    def fetch_metadata(self) -> dict:
        self.last_metadata_source = "none"

        if self.use_cache and not self.refresh_metadata:
            cached = self._load_cached_metadata(fresh_only=True)
            if cached is not None:
                self.last_metadata_source = "cache-fresh"
                return cached

        errors: list[str] = []
        for url in self._metadata_candidates():
            try:
                metadata = self._fetch_json(url)
                if not _looks_like_metadata(metadata):
                    errors.append(f"{url} (payload is not Initializr metadata)")
                    continue
                self._metadata_url = url
                self.last_metadata_source = "network"
                if self.use_cache:
                    self._save_cached_metadata(metadata, source_url=url)
                return metadata
            except Exception as exc:
                errors.append(f"{url} ({exc})")

        if self.use_cache:
            stale = self._load_cached_metadata(fresh_only=False)
            if stale is not None:
                self.last_metadata_source = "cache-stale"
                return stale

        raise RuntimeError(self._build_resolution_error("metadata", errors))

    def download_starter_zip(self, query_params: dict[str, str]) -> bytes:
        query = urlencode(query_params)
        errors: list[str] = []
        for base_url in self._starter_candidates():
            try:
                separator = "&" if "?" in base_url else "?"
                req = Request(
                    f"{base_url}{separator}{query}",
                    headers={"User-Agent": self.user_agent},
                )
                with self._open(req) as response:
                    self._starter_url = base_url
                    return response.read()
            except Exception as exc:
                errors.append(f"{base_url} ({exc})")
        raise RuntimeError(self._build_resolution_error("starter endpoint", errors))

    def build_starter_url(self, query_params: dict[str, str]) -> str:
        base_url = self._starter_url or f"{self.base_url}/starter.zip"
        query = urlencode(query_params)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{query}"

    def cache_info(self) -> dict[str, object]:
        entry = self._read_cache_entry()
        info: dict[str, object] = {
            "exists": entry is not None,
            "path": str(self.cache_path),
            "ttl_seconds": self.cache_ttl_seconds,
        }
        if entry is None:
            return info

        saved_at = float(entry["saved_at"])
        age_seconds = max(0, int(time.time() - saved_at))
        info.update(
            {
                "saved_at": saved_at,
                "age_seconds": age_seconds,
                "is_fresh": age_seconds <= self.cache_ttl_seconds,
                "source_url": entry.get("source_url", ""),
            }
        )
        return info

    def _metadata_candidates(self) -> list[str]:
        candidates: list[str] = []
        if self._metadata_url:
            candidates.append(self._metadata_url)

        discovered = self._discover_endpoints().get("metadata")
        if discovered:
            candidates.append(discovered)

        candidates.extend(
            [
                f"{self.base_url}/metadata/client",
                f"{self.base_url}/metadata",
                self.base_url,
            ]
        )
        return _dedupe(candidates)

    def _starter_candidates(self) -> list[str]:
        candidates: list[str] = []
        if self._starter_url:
            candidates.append(self._starter_url)

        discovered = self._discover_endpoints().get("starter")
        if discovered:
            candidates.append(discovered)

        candidates.append(f"{self.base_url}/starter.zip")
        return _dedupe(candidates)

    def _discover_endpoints(self) -> dict[str, str]:
        if self._discovered_endpoints is not None:
            return self._discovered_endpoints

        request_url = f"{self.base_url}/"
        req = Request(
            request_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/vnd.initializr.v2.1+json, application/json",
            },
        )
        try:
            with self._open(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return {}

        links = payload.get("_links")
        if not isinstance(links, dict):
            return {}

        metadata_url: str | None = None
        starter_url: str | None = None

        for value in links.values():
            href = _extract_href(value)
            if not href:
                continue
            resolved = _strip_uri_template(urljoin(request_url, href))
            if "/metadata" in resolved and metadata_url is None:
                metadata_url = resolved
            if ("starter" in resolved or resolved.endswith(".zip")) and starter_url is None:
                starter_url = resolved
            if metadata_url and starter_url:
                break

        discovered: dict[str, str] = {}
        if metadata_url:
            discovered["metadata"] = metadata_url
        if starter_url:
            discovered["starter"] = starter_url

        if discovered:
            self._discovered_endpoints = discovered
        return discovered

    def _fetch_json(self, url: str) -> dict:
        req = Request(url, headers={"User-Agent": self.user_agent})
        with self._open(req) as response:
            return json.loads(response.read().decode("utf-8"))

    def _open(self, req: Request):
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return urlopen(req, timeout=self.timeout_seconds)
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries or not _is_retryable(exc):
                    raise
                sleep_seconds = self.backoff_seconds * (2**attempt)
                time.sleep(sleep_seconds)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Request failed without a captured error")

    def _read_cache_entry(self) -> dict | None:
        if not self.cache_path.exists():
            return None

        try:
            raw = self.cache_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None

        metadata = payload.get("metadata")
        saved_at = payload.get("saved_at")
        if not isinstance(metadata, dict):
            return None
        if not isinstance(saved_at, (int, float)):
            return None

        return {
            "metadata": metadata,
            "saved_at": float(saved_at),
            "source_url": payload.get("source_url", ""),
        }

    def _load_cached_metadata(self, fresh_only: bool) -> dict | None:
        entry = self._read_cache_entry()
        if entry is None:
            return None

        age_seconds = time.time() - float(entry["saved_at"])
        if fresh_only and age_seconds > self.cache_ttl_seconds:
            return None

        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            return None
        return metadata

    def _save_cached_metadata(self, metadata: dict, source_url: str) -> None:
        payload = {
            "saved_at": time.time(),
            "source_url": source_url,
            "metadata": metadata,
        }
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            # Cache write failure should never break CLI behavior.
            return

    def _build_resolution_error(self, name: str, attempts: list[str]) -> str:
        detail = "; ".join(attempts) if attempts else "no endpoints attempted"
        return (
            f"Unable to resolve Spring Initializr {name}. "
            f"Tried: {detail}. "
            f"If start.spring.io API changed, upgrade this CLI."
        )


def _default_cache_path() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "spring-init" / "metadata.json"

    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        return Path(xdg_cache_home) / "spring-init" / "metadata.json"

    return Path.home() / ".cache" / "spring-init" / "metadata.json"


def _extract_href(link_value: object) -> str | None:
    if isinstance(link_value, list):
        for item in link_value:
            href = _extract_href(item)
            if href:
                return href
        return None

    if isinstance(link_value, dict):
        href = link_value.get("href")
        return href if isinstance(href, str) else None
    return None


def _strip_uri_template(url: str) -> str:
    template_start = url.find("{")
    if template_start >= 0:
        return url[:template_start]
    return url


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _looks_like_metadata(payload: dict) -> bool:
    # Accept when at least one core metadata section follows expected shape.
    for key in ("bootVersion", "type", "language", "packaging"):
        section = payload.get(key)
        if not isinstance(section, dict):
            continue
        values = section.get("values")
        if isinstance(values, list):
            return True

    dependencies = payload.get("dependencies")
    if isinstance(dependencies, dict):
        dep_values = dependencies.get("values")
        if isinstance(dep_values, list):
            return True
    return False


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, OSError))
