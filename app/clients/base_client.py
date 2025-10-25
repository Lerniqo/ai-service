"""Base reusable async HTTP client for internal service-to-service calls.

Features:
 - Lazy / injectable httpx.AsyncClient instance
 - Bearer token auth header (service secret)
 - Centralised GET helper with robust error handling
 - Async context manager support
"""

from __future__ import annotations

from typing import Any, Optional
import httpx
from urllib.parse import urlparse

class ServiceClientError(RuntimeError):
    """Raised when a downstream service returns a non-success response or network error."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

class BaseClient:
    """Abstract base for internal service API clients.

    Subclasses can define class attributes BASE_URL_ENV & SECRET_ENV to allow
    automatic environment variable resolution when explicit values are not passed.
    """

    BASE_URL_ENV: str | None = None
    SECRET_ENV: str | None = None

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        *,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        # Use centralized settings instead of direct os.getenv
        if base_url is None and self.BASE_URL_ENV:
            from app.config import get_settings
            settings = get_settings()
            # For progress service, try the internal URL first
            if self.BASE_URL_ENV == "PROGRESS_SERVICE_BASE_URL":
                base_url = settings.internal_progress_service_url
            else:
                base_url = getattr(settings, self.BASE_URL_ENV, None)
        if secret is None and self.SECRET_ENV:
            from app.config import get_settings
            settings = get_settings()
            secret = getattr(settings, self.SECRET_ENV, None)

        if not base_url:
            raise ValueError("base_url is required (argument or environment variable)")

        # Ensure base_url has a proper protocol
        if not base_url.startswith(("http://", "https://")):
            # Default to https:// for security, but you can adjust this based on your needs
            base_url = f"https://{base_url}"

        # Validate the URL structure
        try:
            parsed = urlparse(base_url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError(f"Invalid base_url format: {base_url}")
        except Exception as e:
            raise ValueError(f"Invalid base_url format: {base_url} - {e}")

        self._base_url = base_url.rstrip("/")
        self._secret = secret
        self._timeout = timeout
        self._external_client_provided = client is not None
        self._client: httpx.AsyncClient | None = client

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self._secret:
                headers["Authorization"] = f"Bearer {self._secret}"
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, headers=headers)
        return self._client

    async def close(self) -> None:
        if self._client and not self._external_client_provided:
            await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> "BaseClient":  # pragma: no cover - trivial
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        await self.close()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    async def _get(self, path: str, *, headers: Optional[dict[str, str]] = None, params: Optional[dict[str, Any]] = None) -> Any:
        """Perform a GET request and return JSON body.

        Args:
            path: Either an absolute URL or path relative to base_url.
            headers: Optional headers to include in the request.
            params: Optional query parameters.
        Raises:
            ServiceClientError on network issues or non-2xx status.
        """
        client = await self._ensure_client()
        # Allow absolute URLs (useful for redirects or full endpoints)
        url = path if path.startswith("http://") or path.startswith("https://") else path
        try:
            resp = await client.get(url, params=params, headers=headers)
        except httpx.RequestError as e:  # network / timeout
            raise ServiceClientError(f"Network error calling service: {e}") from e

        if resp.status_code // 100 != 2:
            # Attempt to parse json body for more diagnostics
            error_payload: Any | None
            try:
                error_payload = resp.json()
            except Exception:  # pragma: no cover - fallback
                error_payload = resp.text
            raise ServiceClientError(
                f"Service responded with HTTP {resp.status_code} at {resp.request.method} {resp.request.url}",
                status_code=resp.status_code,
                payload=error_payload,
            )
        # Return parsed JSON (or raw text if no JSON)
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return resp.json()
        return resp.text

    async def _post(self, path: str, *, json: Optional[dict[str, Any]] = None, headers: Optional[dict[str, str]] = None) -> Any:
        """Perform a POST request and return JSON body.

        Args:
            path: Either an absolute URL or path relative to base_url.
            json: Optional JSON body to send.
            headers: Optional headers to include in the request.
        Raises:
            ServiceClientError on network issues or non-2xx status.
        """
        client = await self._ensure_client()
        # Allow absolute URLs (useful for redirects or full endpoints)
        url = path if path.startswith("http://") or path.startswith("https://") else path
        try:
            resp = await client.post(url, json=json, headers=headers)
        except httpx.RequestError as e:  # network / timeout
            raise ServiceClientError(f"Network error calling service: {e}") from e

        if resp.status_code // 100 != 2:
            # Attempt to parse json body for more diagnostics
            error_payload: Any | None
            try:
                error_payload = resp.json()
            except Exception:  # pragma: no cover - fallback
                error_payload = resp.text
            raise ServiceClientError(
                f"Service responded with HTTP {resp.status_code} at {resp.request.method} {resp.request.url}",
                status_code=resp.status_code,
                payload=error_payload,
            )
        # Return parsed JSON (or raw text if no JSON)
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return resp.json()
        return resp.text

    # Convenience property (read-only)
    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def secret(self) -> Optional[str]:
        return self._secret
