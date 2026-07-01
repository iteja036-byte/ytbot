"""Unified AI client for the video creation platform.

This module exposes :class:`AIClient`, a thin, production-grade facade in
front of multiple model providers:

* OpenAI
* Google Gemini
* Anthropic Claude
* Ollama (local)
* OpenRouter

Design goals
------------
* **One interface, many backends** - the public methods never leak
  provider-specific details to the caller.
* **Provider abstraction** - every backend implements the same internal
  :class:`_ProviderAdapter` contract, so adding a new vendor is a matter
  of writing a single new adapter.
* **Resilience** - automatic retries with exponential backoff for
  transient errors (rate limits, 5xx, network blips), strict timeouts,
  and structured logging at every step.
* **Configurable** - everything is driven by environment variables
  (``AI_*`` namespace) and can be overridden per-instance.
* **Type-safe** - PEP 604 unions, ``Self`` typing, fully annotated
  public surface.
* **Testable** - the HTTP transport is injected, so unit tests can
  stub providers without monkey-patching globals.

Environment variables
---------------------
``AI_DEFAULT_PROVIDER``
    Default provider to use when none is given (``openai``, ``gemini``,
    ``anthropic``, ``ollama``, ``openrouter``). Default: ``openai``.
``AI_DEFAULT_MODEL``
    Default model identifier. Default: ``gpt-4o-mini``.
``AI_DEFAULT_TIMEOUT``
    Default request timeout in seconds. Default: ``60``.
``AI_MAX_RETRIES``
    Default maximum number of retry attempts. Default: ``3``.
``AI_RETRY_BACKOFF``
    Initial backoff delay in seconds (doubles each attempt).
    Default: ``1.0``.
``AI_LOG_LEVEL``
    Logging level (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
    Default: ``INFO``.

Provider-specific variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~
``OPENAI_API_KEY``              OpenAI bearer token.
``OPENAI_BASE_URL``             Override the OpenAI base URL.
``OPENAI_ORG_ID``               Optional organization id.

``GEMINI_API_KEY``              Google Gemini API key.
``GEMINI_BASE_URL``             Override the Gemini REST base URL.

``ANTHROPIC_API_KEY``           Anthropic API key.
``ANTHROPIC_BASE_URL``          Override Anthropic's base URL.
``ANTHROPIC_VERSION``           Anthropic API version header.

``OLLAMA_BASE_URL``             Ollama server URL. Default:
                                ``http://localhost:11434``.

``OPENROUTER_API_KEY``          OpenRouter API key.
``OPENROUTER_BASE_URL``         Override OpenRouter base URL. Default:
                                ``https://openrouter.ai/api/v1``.
``OPENROUTER_APP_NAME``         Sent as ``X-Title`` header.
``OPENROUTER_HTTP_REFERER``     Sent as ``HTTP-Referer`` header.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Mapping,
    Protocol,
    Sequence,
    TypeAlias,
    runtime_checkable,
)

import requests
from requests import Response, Session

# ``google.generativeai`` is optional. We import it lazily inside the
# Gemini adapter to keep this module importable in environments where
# it is not installed (and to avoid noisy deprecation warnings at
# import time).

__all__ = [
    "AIClient",
    "AIProvider",
    "AIClientError",
    "AIProviderError",
    "AIAuthenticationError",
    "AIRateLimitError",
    "AITimeoutError",
    "AIResponseError",
    "AIValidationError",
    "AIConfigurationError",
    "GenerationRequest",
    "ImageGenerationRequest",
    "ImageAnalysisRequest",
    "AudioTranscriptionRequest",
    "HealthCheckResult",
    "ImageResult",
    "AudioTranscriptionResult",
    "AIClientSettings",
    "configure_logging",
]

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

# A very loose type alias for JSON-compatible data. ``Any`` keeps the
# surface ergonomic for callers while still giving static analyzers
# enough information to flag obvious mistakes.
JSONScalar: TypeAlias = "str | int | float | bool | None"
JSONValue: TypeAlias = "JSONScalar | list[JSONValue] | dict[str, JSONValue] | Any"
JSONObject: TypeAlias = "dict[str, JSONValue]"
Messages: TypeAlias = "list[dict[str, str]]"


class AIProvider(str, Enum):
    """Enumeration of supported AI providers.

    Members
    -------
    OPENAI
        OpenAI's hosted models (``gpt-*``, ``o1-*``, ``dall-e-*``,
        ``whisper-*``).
    GEMINI
        Google's Gemini family of models.
    ANTHROPIC
        Anthropic's Claude family of models.
    OLLAMA
        A locally running Ollama server.
    OPENROUTER
        OpenRouter's multi-vendor router.
    """

    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

    @classmethod
    def coerce(cls, value: str | "AIProvider") -> "AIProvider":
        """Normalise a string-or-enum into an :class:`AIProvider`.

        Parameters
        ----------
        value
            Either an :class:`AIProvider` instance or its case-insensitive
            string form (``"openai"``, ``"OpenAI"`` etc.).

        Returns
        -------
        AIProvider
            The corresponding enum member.

        Raises
        ------
        AIValidationError
            If ``value`` is not a recognised provider.
        """
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise AIValidationError(
                f"Provider must be a string or AIProvider, got {type(value).__name__}"
            )
        normalised = value.strip().lower()
        for member in cls:
            if member.value == normalised:
                return member
        raise AIValidationError(f"Unknown AI provider: {value!r}")


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AIClientSettings:
    """Runtime configuration for :class:`AIClient`.

    The dataclass is intentionally permissive: unknown attributes
    passed via :meth:`from_env` are ignored so future providers can
    introduce new variables without breaking older deployments.
    """

    default_provider: AIProvider = AIProvider.OPENAI
    default_model: str = "gpt-4o-mini"
    timeout: float = 60.0
    max_retries: int = 3
    retry_backoff: float = 1.0
    log_level: str = "INFO"

    # Per-provider overrides -------------------------------------------------
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_org_id: str | None = None

    gemini_api_key: str | None = None
    gemini_base_url: str = (
        "https://generativelanguage.googleapis.com/v1beta"
    )

    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_version: str = "2023-06-01"

    ollama_base_url: str = "http://localhost:11434"

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "ytbot"
    openrouter_http_referer: str = "https://ytbot.local"

    # ----- Constructors ----------------------------------------------------

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AIClientSettings":
        """Build an :class:`AIClientSettings` from process environment.

        Parameters
        ----------
        env
            Mapping to read from. ``None`` means :data:`os.environ`.
            Tests can pass a stub mapping.

        Returns
        -------
        AIClientSettings
            A populated configuration object.
        """
        src: Mapping[str, str] = os.environ if env is None else env

        def _get(key: str, default: str | None = None) -> str | None:
            value = src.get(key)
            return value if value is not None and value != "" else default

        def _get_float(key: str, default: float) -> float:
            raw = _get(key)
            if raw is None:
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default

        def _get_int(key: str, default: int) -> int:
            raw = _get(key)
            if raw is None:
                return default
            try:
                return int(raw)
            except (TypeError, ValueError):
                return default

        try:
            default_provider = AIProvider.coerce(
                _get("AI_DEFAULT_PROVIDER", "openai") or "openai"
            )
        except AIValidationError:
            default_provider = AIProvider.OPENAI

        return cls(
            default_provider=default_provider,
            default_model=_get("AI_DEFAULT_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
            timeout=_get_float("AI_DEFAULT_TIMEOUT", 60.0),
            max_retries=_get_int("AI_MAX_RETRIES", 3),
            retry_backoff=_get_float("AI_RETRY_BACKOFF", 1.0),
            log_level=_get("AI_LOG_LEVEL", "INFO") or "INFO",
            openai_api_key=_get("OPENAI_API_KEY"),
            openai_base_url=_get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            or "https://api.openai.com/v1",
            openai_org_id=_get("OPENAI_ORG_ID"),
            gemini_api_key=_get("GEMINI_API_KEY"),
            gemini_base_url=_get(
                "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
            )
            or "https://generativelanguage.googleapis.com/v1beta",
            anthropic_api_key=_get("ANTHROPIC_API_KEY"),
            anthropic_base_url=_get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
            or "https://api.anthropic.com",
            anthropic_version=_get("ANTHROPIC_VERSION", "2023-06-01")
            or "2023-06-01",
            ollama_base_url=_get("OLLAMA_BASE_URL", "http://localhost:11434")
            or "http://localhost:11434",
            openrouter_api_key=_get("OPENROUTER_API_KEY"),
            openrouter_base_url=_get(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            )
            or "https://openrouter.ai/api/v1",
            openrouter_app_name=_get("OPENROUTER_APP_NAME", "ytbot") or "ytbot",
            openrouter_http_referer=_get(
                "OPENROUTER_HTTP_REFERER", "https://ytbot.local"
            )
            or "https://ytbot.local",
        )

    # ----- Helpers ---------------------------------------------------------

    def api_key_for(self, provider: AIProvider) -> str | None:
        """Return the API key configured for ``provider`` (if any)."""
        mapping: dict[AIProvider, str | None] = {
            AIProvider.OPENAI: self.openai_api_key,
            AIProvider.GEMINI: self.gemini_api_key,
            AIProvider.ANTHROPIC: self.anthropic_api_key,
            AIProvider.OPENROUTER: self.openrouter_api_key,
            AIProvider.OLLAMA: None,  # Ollama is local; no key needed.
        }
        return mapping.get(provider)


# ---------------------------------------------------------------------------
# Request dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GenerationRequest:
    """Parameters for text or JSON generation."""

    prompt: str
    model: str | None = None
    system: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 1.0
    stop: Sequence[str] | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ImageGenerationRequest:
    """Parameters for text-to-image generation."""

    prompt: str
    model: str | None = None
    size: str = "1024x1024"
    n: int = 1
    quality: str | None = None
    style: str | None = None
    negative_prompt: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ImageAnalysisRequest:
    """Parameters for vision / image-understanding calls."""

    image: str | bytes
    prompt: str = "Describe this image in detail."
    model: str | None = None
    detail: str = "auto"  # OpenAI-specific; ignored elsewhere.
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AudioTranscriptionRequest:
    """Parameters for speech-to-text calls."""

    audio: str | bytes
    model: str | None = None
    language: str | None = None
    prompt: str | None = None
    response_format: str = "json"
    temperature: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class HealthCheckResult:
    """Outcome of a :meth:`AIClient.health_check` call."""

    provider: AIProvider
    healthy: bool
    latency_ms: float | None
    detail: str | None = None
    error: str | None = None


@dataclass(slots=True)
class ImageResult:
    """A single generated image."""

    b64_json: str | None = None
    url: str | None = None
    revised_prompt: str | None = None
    mime_type: str = "image/png"
    raw: JSONObject | None = None


@dataclass(slots=True)
class AudioTranscriptionResult:
    """The output of a transcription call."""

    text: str
    language: str | None = None
    duration: float | None = None
    segments: Sequence[JSONObject] = field(default_factory=tuple)
    raw: JSONObject | None = None


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class AIClientError(Exception):
    """Base class for all exceptions raised by :class:`AIClient`."""


class AIProviderError(AIClientError):
    """A provider returned a non-recoverable error.

    Parameters
    ----------
    message
        Human-readable description.
    provider
        The provider that produced the error.
    status_code
        HTTP status code, if applicable.
    body
        Raw response body, if captured.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: AIProvider | None = None,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        bits = [super().__str__()]
        if self.provider is not None:
            bits.append(f"provider={self.provider.value}")
        if self.status_code is not None:
            bits.append(f"status={self.status_code}")
        return " | ".join(bits)


class AIValidationError(AIProviderError):
    """Caller-supplied arguments are invalid."""


class AIConfigurationError(AIProviderError):
    """The client is mis-configured (missing API key, bad URL, ...)."""


class AIAuthenticationError(AIProviderError):
    """The provider rejected our credentials (HTTP 401/403)."""


class AIRateLimitError(AIProviderError):
    """The provider asked us to slow down (HTTP 429)."""


class AITimeoutError(AIProviderError):
    """The provider took longer than the configured timeout."""


class AIResponseError(AIProviderError):
    """The provider returned an unexpected payload we cannot parse."""


# ---------------------------------------------------------------------------
# Transport protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class _SupportsRequests(Protocol):
    """Structural type for objects that behave like :class:`requests.Session`."""

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Any = ...,
        json: Any = ...,
        data: Any = ...,
        headers: Mapping[str, str] | None = ...,
        timeout: float | None = ...,
        files: Any = ...,
    ) -> Response: ...


# ---------------------------------------------------------------------------
# Provider adapter contract
# ---------------------------------------------------------------------------


class _ProviderAdapter(ABC):
    """Internal contract every provider backend must satisfy.

    The adapter receives fully validated dataclass request objects and
    is responsible for translating them to the provider's native
    protocol. Returning raw :class:`dict` payloads from ``_request``
    keeps the surface uniform across vendors.
    """

    provider: AIProvider

    def __init__(self, settings: AIClientSettings, transport: _SupportsRequests) -> None:
        self._settings = settings
        self._transport = transport
        self._log = logging.getLogger(f"{__name__}.{self.provider.value}")

    # ----- Public entry points -------------------------------------------

    @abstractmethod
    def generate_text(self, request: GenerationRequest) -> str:
        """Return a plain-text completion."""

    @abstractmethod
    def generate_json(self, request: GenerationRequest) -> JSONObject:
        """Return a JSON object completion."""

    @abstractmethod
    def generate_image(self, request: ImageGenerationRequest) -> list[ImageResult]:
        """Return one or more generated images."""

    @abstractmethod
    def analyze_image(self, request: ImageAnalysisRequest) -> str:
        """Return a textual description/analysis of the given image."""

    @abstractmethod
    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        """Return a transcription of the given audio."""

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Return a lightweight health probe."""

    # ----- Shared JSON parsing -------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> JSONObject:
        """Parse a JSON object string, tolerating ````json ... ```` fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if "\n" in cleaned:
                cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rstrip("`").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AIResponseError(
                f"Failed to decode JSON from model: {exc}",
                body=cleaned[:512],
            ) from exc
        if not isinstance(parsed, dict):
            raise AIResponseError(
                "Model did not return a JSON object",
                body=cleaned[:512],
            )
        return parsed

    # ----- Shared HTTP plumbing ------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        json: JSONObject | None = None,
        params: Mapping[str, Any] | None = None,
        data: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        files: Any = None,
    ) -> JSONObject:
        """Execute an HTTP call with retries and rich error handling.

        Returns
        -------
        dict
            The parsed JSON body. Returns an empty dict for ``204 No
            Content`` responses.

        Raises
        ------
        AITimeoutError
            If the call exceeds ``timeout``.
        AIAuthenticationError
            If the provider returns 401/403.
        AIRateLimitError
            If the provider returns 429.
        AIProviderError
            For any other non-2xx response.
        """
        attempt = 0
        backoff = self._settings.retry_backoff
        last_error: AIProviderError | None = None

        while True:
            attempt += 1
            try:
                self._log.debug(
                    "HTTP %s %s attempt=%d", method, url, attempt
                )
                response = self._transport.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    timeout=timeout if timeout is not None else self._settings.timeout,
                    files=files,
                )
            except requests.exceptions.Timeout as exc:
                last_error = AITimeoutError(
                    f"Timeout after {self._settings.timeout}s calling {url}",
                    provider=self.provider,
                )
                self._log.warning("Timeout on %s %s: %s", method, url, exc)
            except requests.exceptions.RequestException as exc:
                last_error = AIProviderError(
                    f"Network error calling {url}: {exc}",
                    provider=self.provider,
                )
                self._log.warning("Network error on %s %s: %s", method, url, exc)
            else:
                if response.ok:
                    if response.status_code == 204 or not response.content:
                        return {}
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise AIResponseError(
                            f"Provider returned non-JSON response: {exc}",
                            provider=self.provider,
                            status_code=response.status_code,
                            body=response.text[:1024],
                        ) from exc
                last_error = self._build_error(response)
                if not self._should_retry(response.status_code, attempt):
                    raise last_error
                self._log.warning(
                    "Retryable status %d from %s %s (attempt %d/%d)",
                    response.status_code,
                    method,
                    url,
                    attempt,
                    self._settings.max_retries,
                )

            if attempt > self._settings.max_retries:
                assert last_error is not None  # for type-checkers
                raise last_error

            # Exponential backoff with full jitter to avoid thundering
            # herd in bursty scenarios.
            sleep_for = backoff * (2 ** (attempt - 1))
            sleep_for += random.uniform(0, sleep_for * 0.25)
            self._log.debug("Sleeping %.2fs before retry", sleep_for)
            time.sleep(sleep_for)

    # ----- Helpers --------------------------------------------------------

    def _build_error(self, response: Response) -> AIProviderError:
        status = response.status_code
        body = response.text[:1024] if response.text else None
        message = f"Provider returned HTTP {status}"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                err = payload.get("error")
                if isinstance(err, dict) and "message" in err:
                    message = f"{message}: {err['message']}"
                elif "message" in payload:
                    message = f"{message}: {payload['message']}"
        except ValueError:
            pass

        if status in (401, 403):
            return AIAuthenticationError(
                message, provider=self.provider, status_code=status, body=body
            )
        if status == 429:
            return AIRateLimitError(
                message, provider=self.provider, status_code=status, body=body
            )
        if 500 <= status < 600:
            return AIProviderError(
                message, provider=self.provider, status_code=status, body=body
            )
        return AIResponseError(
            message, provider=self.provider, status_code=status, body=body
        )

    @staticmethod
    def _should_retry(status_code: int, attempt: int) -> bool:
        if attempt >= 1 and status_code in (408, 425, 429):
            return True
        if 500 <= status_code < 600:
            return True
        return False

    @staticmethod
    def _encode_image(image: str | bytes) -> tuple[str, str]:
        """Return ``(data, mime)`` for an image path, URL or raw bytes.

        Bytes shorter than 4 KiB and not starting with a filesystem
        marker are treated as raw image data. Otherwise we treat the
        value as a filesystem path. URLs are returned verbatim; the
        caller is expected to fetch them itself before calling.
        """
        if isinstance(image, bytes):
            return base64.b64encode(image).decode("ascii"), _guess_mime(image)
        if image.startswith(("http://", "https://", "data:")):
            return image, "image/url"
        # Treat as a filesystem path
        if not os.path.isfile(image):
            raise AIValidationError(f"Image file not found: {image}")
        with open(image, "rb") as fh:
            data = fh.read()
        return base64.b64encode(data).decode("ascii"), _guess_mime(data, path=image)


def _guess_mime(data: bytes, *, path: str | None = None) -> str:
    """Best-effort MIME-type guess for raw bytes or a file path."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if path is not None:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        return {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }.get(ext, "application/octet-stream")
    return "application/octet-stream"


# ---------------------------------------------------------------------------
# OpenAI adapter
# ---------------------------------------------------------------------------


class _OpenAIAdapter(_ProviderAdapter):
    provider = AIProvider.OPENAI

    def _headers(self) -> dict[str, str]:
        if not self._settings.openai_api_key:
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured", provider=self.provider
            )
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._settings.openai_org_id:
            headers["OpenAI-Organization"] = self._settings.openai_org_id
        return headers

    def _url(self, path: str) -> str:
        return f"{self._settings.openai_base_url.rstrip('/')}{path}"

    # ----- Generation -----------------------------------------------------

    def _chat(
        self,
        request: GenerationRequest,
        *,
        response_format: Mapping[str, str] | None = None,
    ) -> JSONObject:
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, Any] = {
            "model": request.model or self._settings.default_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
        }
        if request.stop:
            payload["stop"] = list(request.stop)
        if response_format is not None:
            payload["response_format"] = dict(response_format)
        for key, value in request.metadata.items():
            payload[key] = value

        return self._request(
            "POST",
            self._url("/chat/completions"),
            json=payload,
            headers=self._headers(),
        )

    def generate_text(self, request: GenerationRequest) -> str:
        body = self._chat(request)
        return self._extract_text(body)

    def generate_json(self, request: GenerationRequest) -> JSONObject:
        body = self._chat(
            request, response_format={"type": "json_object"}
        )
        content = self._extract_text(body)
        return self._parse_json(content)

    def _extract_text(self, body: JSONObject) -> str:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AIResponseError(
                "OpenAI response missing 'choices'",
                provider=self.provider,
                body=json.dumps(body)[:512],
            )
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise AIResponseError(
                "OpenAI message content is not a string",
                provider=self.provider,
                body=json.dumps(body)[:512],
            )
        return content

    # ----- Image generation ----------------------------------------------

    def generate_image(self, request: ImageGenerationRequest) -> list[ImageResult]:
        model = request.model or "dall-e-3"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": request.prompt,
            "n": request.n,
            "size": request.size,
        }
        if request.quality:
            payload["quality"] = request.quality
        if request.style:
            payload["style"] = request.style
        for key, value in request.metadata.items():
            payload[key] = value

        body = self._request(
            "POST",
            self._url("/images/generations"),
            json=payload,
            headers=self._headers(),
        )
        return self._parse_images(body)

    @staticmethod
    def _parse_images(body: JSONObject) -> list[ImageResult]:
        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise AIResponseError(
                "OpenAI image response missing 'data'",
                body=json.dumps(body)[:512],
            )
        results: list[ImageResult] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            results.append(
                ImageResult(
                    b64_json=item.get("b64_json"),
                    url=item.get("url"),
                    revised_prompt=item.get("revised_prompt"),
                )
            )
        if not results:
            raise AIResponseError(
                "OpenAI image response contained no usable items",
                body=json.dumps(body)[:512],
            )
        return results

    # ----- Vision / image analysis --------------------------------------

    def analyze_image(self, request: ImageAnalysisRequest) -> str:
        data, mime = self._encode_image(request.image)
        url_part: dict[str, Any]
        if mime == "image/url":
            url_part = {"type": "image_url", "image_url": {"url": data, "detail": request.detail}}
        else:
            url_part = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{data}",
                    "detail": request.detail,
                },
            }
        payload: dict[str, Any] = {
            "model": request.model or self._settings.default_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": request.prompt},
                        url_part,
                    ],
                }
            ],
            "max_tokens": 1024,
        }
        for key, value in request.metadata.items():
            payload[key] = value
        body = self._request(
            "POST",
            self._url("/chat/completions"),
            json=payload,
            headers=self._headers(),
        )
        return self._extract_text(body)

    # ----- Audio transcription ------------------------------------------

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        if not self._settings.openai_api_key:
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured", provider=self.provider
            )
        model = request.model or "whisper-1"
        files = self._build_audio_files(request.audio)
        data: dict[str, Any] = {
            "model": model,
            "response_format": request.response_format,
            "temperature": request.temperature,
        }
        if request.language:
            data["language"] = request.language
        if request.prompt:
            data["prompt"] = request.prompt
        for key, value in request.metadata.items():
            data[key] = value

        body = self._request(
            "POST",
            self._url("/audio/transcriptions"),
            data=data,
            files=files,
            headers={
                "Authorization": f"Bearer {self._settings.openai_api_key}",
            },
        )
        return self._parse_transcription(body, request.response_format)

    @staticmethod
    def _build_audio_files(audio: str | bytes) -> dict[str, tuple[str, bytes, str]]:
        if isinstance(audio, bytes):
            return {"file": ("audio.mp3", audio, "audio/mpeg")}
        if not os.path.isfile(audio):
            raise AIValidationError(f"Audio file not found: {audio}")
        with open(audio, "rb") as fh:
            data = fh.read()
        mime = "audio/mpeg" if audio.lower().endswith(".mp3") else "application/octet-stream"
        return {"file": (os.path.basename(audio), data, mime)}

    @staticmethod
    def _parse_transcription(
        body: JSONObject, response_format: str
    ) -> AudioTranscriptionResult:
        text = body.get("text")
        if not isinstance(text, str):
            raise AIResponseError(
                "Whisper response missing 'text'",
                body=json.dumps(body)[:512],
            )
        segments: tuple[JSONObject, ...] = ()
        seg = body.get("segments")
        if isinstance(seg, list):
            segments = tuple(item for item in seg if isinstance(item, dict))
        language = body.get("language") if isinstance(body.get("language"), str) else None
        duration = body.get("duration") if isinstance(body.get("duration"), (int, float)) else None
        return AudioTranscriptionResult(
            text=text,
            language=language,
            duration=float(duration) if duration is not None else None,
            segments=segments,
            raw=body,
        )

    # ----- Health --------------------------------------------------------

    def health_check(self) -> HealthCheckResult:
        if not self._settings.openai_api_key:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=None,
                detail="OPENAI_API_KEY is not configured",
                error="missing api key",
            )
        start = time.perf_counter()
        try:
            self._request(
                "GET",
                self._url("/models"),
                headers=self._headers(),
            )
        except AIProviderError as exc:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                detail=str(exc),
                error=exc.__class__.__name__,
            )
        return HealthCheckResult(
            provider=self.provider,
            healthy=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


# ---------------------------------------------------------------------------
# OpenRouter adapter (OpenAI-compatible)
# ---------------------------------------------------------------------------


class _OpenRouterAdapter(_OpenAIAdapter):
    provider = AIProvider.OPENROUTER

    def _headers(self) -> dict[str, str]:
        if not self._settings.openrouter_api_key:
            raise AIConfigurationError(
                "OPENROUTER_API_KEY is not configured", provider=self.provider
            )
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Title": self._settings.openrouter_app_name,
            "HTTP-Referer": self._settings.openrouter_http_referer,
        }

    def _url(self, path: str) -> str:
        return f"{self._settings.openrouter_base_url.rstrip('/')}{path}"

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        raise AIProviderError(
            "OpenRouter does not currently expose an audio transcription endpoint",
            provider=self.provider,
        )

    def generate_image(self, request: ImageGenerationRequest) -> list[ImageResult]:
        # Most OpenRouter models support image generation via the chat
        # completions endpoint; we delegate to the base class' text
        # path and then surface the response as a single image with the
        # raw payload attached for callers that need to interpret it.
        chat_request = GenerationRequest(
            prompt=request.prompt,
            model=request.model,
            system=(
                "You generate images. Respond with a JSON object containing a "
                "'url' or 'b64_json' field describing the generated image."
            ),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            metadata=request.metadata,
        )
        body = self._chat(chat_request)
        content = self._extract_text(body)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return [ImageResult(b64_json=None, url=None, raw={"text": content})]
        if not isinstance(parsed, dict):
            return [ImageResult(b64_json=None, url=None, raw={"text": content})]
        return [
            ImageResult(
                b64_json=parsed.get("b64_json") if isinstance(parsed.get("b64_json"), str) else None,
                url=parsed.get("url") if isinstance(parsed.get("url"), str) else None,
            )
        ]


# ---------------------------------------------------------------------------
# Gemini adapter
# ---------------------------------------------------------------------------


class _GeminiAdapter(_ProviderAdapter):
    provider = AIProvider.GEMINI

    def _require_key(self) -> str:
        key = self._settings.gemini_api_key
        if not key:
            raise AIConfigurationError(
                "GEMINI_API_KEY is not configured", provider=self.provider
            )
        return key

    def _url(self, path: str) -> str:
        return f"{self._settings.gemini_base_url.rstrip('/')}{path}"

    # ----- Helpers --------------------------------------------------------

    def _build_contents(
        self, prompt: str, system: str | None
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        contents: dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        system_instruction: dict[str, Any] | None = None
        if system:
            system_instruction = {
                "role": "system",
                "parts": [{"text": system}],
            }
        return contents, system_instruction

    def _generation_config(
        self,
        temperature: float,
        max_tokens: int,
        top_p: float,
        response_mime_type: str | None = None,
    ) -> dict[str, Any]:
        cfg: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": top_p,
        }
        if response_mime_type:
            cfg["responseMimeType"] = response_mime_type
        return cfg

    def _call_generate(
        self,
        model: str,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 1.0,
        response_mime_type: str | None = None,
        extra_body: Mapping[str, Any] | None = None,
    ) -> JSONObject:
        contents, system_instruction = self._build_contents(prompt, system)
        if system_instruction:
            contents["systemInstruction"] = system_instruction
        body: dict[str, Any] = {
            **contents,
            "generationConfig": self._generation_config(
                temperature, max_tokens, top_p, response_mime_type
            ),
        }
        if extra_body:
            body.update(dict(extra_body))
        url = self._url(f"/models/{model}:generateContent")
        return self._request(
            "POST",
            url,
            params={"key": self._require_key()},
            json=body,
        )

    @staticmethod
    def _extract_text(body: JSONObject) -> str:
        candidates = body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AIResponseError(
                "Gemini response missing 'candidates'",
                body=json.dumps(body)[:512],
            )
        content = candidates[0].get("content") or {}
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list) or not parts:
            raise AIResponseError(
                "Gemini response missing content parts",
                body=json.dumps(body)[:512],
            )
        texts: list[str] = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
        if not texts:
            raise AIResponseError(
                "Gemini response had no text parts",
                body=json.dumps(body)[:512],
            )
        return "".join(texts)

    # ----- Public methods -----------------------------------------------

    def generate_text(self, request: GenerationRequest) -> str:
        body = self._call_generate(
            request.model or self._settings.default_model,
            prompt=request.prompt,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
        )
        return self._extract_text(body)

    def generate_json(self, request: GenerationRequest) -> JSONObject:
        body = self._call_generate(
            request.model or self._settings.default_model,
            prompt=request.prompt,
            system=request.system or "Respond with a valid JSON object only.",
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            response_mime_type="application/json",
        )
        text = self._extract_text(body)
        return self._parse_json(text)

    def generate_image(self, request: ImageGenerationRequest) -> list[ImageResult]:
        # Gemini returns images via the Imagen endpoint when available.
        model = request.model or "imagen-3.0-generate-002"
        body: dict[str, Any] = {
            "instances": [{"prompt": request.prompt}],
            "parameters": {"sampleCount": request.n},
        }
        if request.negative_prompt:
            body["instances"][0]["negativePrompt"] = request.negative_prompt
        url = self._url(f"/models/{model}:predict")
        response = self._request(
            "POST",
            url,
            params={"key": self._require_key()},
            json=body,
        )
        predictions = response.get("predictions")
        if not isinstance(predictions, list) or not predictions:
            raise AIResponseError(
                "Imagen response missing 'predictions'",
                body=json.dumps(response)[:512],
            )
        results: list[ImageResult] = []
        for pred in predictions:
            if not isinstance(pred, dict):
                continue
            b64 = pred.get("bytesBase64Encoded")
            mime = pred.get("mimeType") or "image/png"
            results.append(
                ImageResult(
                    b64_json=b64 if isinstance(b64, str) else None,
                    mime_type=mime if isinstance(mime, str) else "image/png",
                )
            )
        if not results:
            raise AIResponseError(
                "Imagen response contained no usable predictions",
                body=json.dumps(response)[:512],
            )
        return results

    def analyze_image(self, request: ImageAnalysisRequest) -> str:
        data, mime = self._encode_image(request.image)
        if mime == "image/url":
            # Gemini doesn't accept URLs directly; require base64.
            raise AIValidationError(
                "Gemini analyze_image requires a local file or raw bytes, not a URL"
            )
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": request.prompt},
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": data,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {"maxOutputTokens": 1024},
        }
        url = self._url(
            f"/models/{request.model or self._settings.default_model}:generateContent"
        )
        response = self._request(
            "POST",
            url,
            params={"key": self._require_key()},
            json=body,
        )
        return self._extract_text(response)

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        # Gemini handles audio via multimodal generation. We use a
        # text-to-text call that returns the transcript.
        data, mime = self._encode_audio(request.audio)
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                request.prompt
                                or "Transcribe the following audio verbatim. "
                                "Respond with the transcript only."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": data,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {"maxOutputTokens": 4096},
        }
        url = self._url(
            f"/models/{request.model or self._settings.default_model}:generateContent"
        )
        response = self._request(
            "POST",
            url,
            params={"key": self._require_key()},
            json=body,
        )
        text = self._extract_text(response)
        return AudioTranscriptionResult(
            text=text.strip(),
            language=request.language,
            raw=response,
        )

    @staticmethod
    def _encode_audio(audio: str | bytes) -> tuple[str, str]:
        if isinstance(audio, bytes):
            return base64.b64encode(audio).decode("ascii"), "audio/mpeg"
        if audio.startswith(("http://", "https://")):
            raise AIValidationError(
                "Gemini transcribe_audio requires a local file or raw bytes, not a URL"
            )
        if not os.path.isfile(audio):
            raise AIValidationError(f"Audio file not found: {audio}")
        with open(audio, "rb") as fh:
            data = fh.read()
        ext = os.path.splitext(audio)[1].lower()
        mime = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".flac": "audio/flac",
            ".webm": "audio/webm",
        }.get(ext, "application/octet-stream")
        return base64.b64encode(data).decode("ascii"), mime

    def health_check(self) -> HealthCheckResult:
        if not self._settings.gemini_api_key:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=None,
                detail="GEMINI_API_KEY is not configured",
                error="missing api key",
            )
        start = time.perf_counter()
        try:
            self._request(
                "GET",
                self._url("/models"),
                params={"key": self._settings.gemini_api_key},
            )
        except AIProviderError as exc:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                detail=str(exc),
                error=exc.__class__.__name__,
            )
        return HealthCheckResult(
            provider=self.provider,
            healthy=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


# ---------------------------------------------------------------------------
# Anthropic adapter
# ---------------------------------------------------------------------------


class _AnthropicAdapter(_ProviderAdapter):
    provider = AIProvider.ANTHROPIC

    def _require_key(self) -> str:
        key = self._settings.anthropic_api_key
        if not key:
            raise AIConfigurationError(
                "ANTHROPIC_API_KEY is not configured", provider=self.provider
            )
        return key

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._require_key(),
            "anthropic-version": self._settings.anthropic_version,
            "content-type": "application/json",
            "accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self._settings.anthropic_base_url.rstrip('/')}{path}"

    # ----- Public methods -----------------------------------------------

    def _messages(
        self,
        request: GenerationRequest,
        *,
        json_mode: bool = False,
    ) -> JSONObject:
        system_prompt = request.system
        if json_mode and not system_prompt:
            system_prompt = "Respond with a single, valid JSON object and nothing else."

        body: dict[str, Any] = {
            "model": request.model or self._settings.default_model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt
        if request.stop:
            body["stop_sequences"] = list(request.stop)
        for key, value in request.metadata.items():
            body[key] = value
        return body

    def generate_text(self, request: GenerationRequest) -> str:
        body = self._messages(request)
        response = self._request(
            "POST", self._url("/v1/messages"), json=body, headers=self._headers()
        )
        return self._extract_text(response)

    def generate_json(self, request: GenerationRequest) -> JSONObject:
        body = self._messages(request, json_mode=True)
        response = self._request(
            "POST", self._url("/v1/messages"), json=body, headers=self._headers()
        )
        return self._parse_json(self._extract_text(response))

    @staticmethod
    def _extract_text(body: JSONObject) -> str:
        content = body.get("content")
        if not isinstance(content, list) or not content:
            raise AIResponseError(
                "Anthropic response missing 'content'",
                body=json.dumps(body)[:512],
            )
        parts: list[str] = []
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ):
                parts.append(block["text"])
        if not parts:
            raise AIResponseError(
                "Anthropic response had no text blocks",
                body=json.dumps(body)[:512],
            )
        return "".join(parts)

    def generate_image(self, request: ImageGenerationRequest) -> list[ImageResult]:
        # Claude does not provide native image generation; we return a
        # descriptive error so callers can fall back to a different
        # provider instead of silently producing nothing.
        raise AIProviderError(
            "Anthropic Claude does not provide image generation",
            provider=self.provider,
        )

    def analyze_image(self, request: ImageAnalysisRequest) -> str:
        data, mime = self._encode_image(request.image)
        if mime == "image/url":
            raise AIValidationError(
                "Anthropic analyze_image requires a local file or raw bytes, not a URL"
            )
        body: dict[str, Any] = {
            "model": request.model or self._settings.default_model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": data,
                            },
                        },
                        {"type": "text", "text": request.prompt},
                    ],
                }
            ],
        }
        for key, value in request.metadata.items():
            body[key] = value
        response = self._request(
            "POST", self._url("/v1/messages"), json=body, headers=self._headers()
        )
        return self._extract_text(response)

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        raise AIProviderError(
            "Anthropic Claude does not provide audio transcription",
            provider=self.provider,
        )

    def health_check(self) -> HealthCheckResult:
        if not self._settings.anthropic_api_key:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=None,
                detail="ANTHROPIC_API_KEY is not configured",
                error="missing api key",
            )
        # Anthropic doesn't expose a public health endpoint, so we send
        # a tiny ping message instead.
        start = time.perf_counter()
        try:
            self._request(
                "POST",
                self._url("/v1/messages"),
                json={
                    "model": self._settings.default_model,
                    "max_tokens": 8,
                    "messages": [{"role": "user", "content": "ping"}],
                },
                headers=self._headers(),
                timeout=min(self._settings.timeout, 15.0),
            )
        except AIProviderError as exc:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                detail=str(exc),
                error=exc.__class__.__name__,
            )
        return HealthCheckResult(
            provider=self.provider,
            healthy=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


# ---------------------------------------------------------------------------
# Ollama adapter
# ---------------------------------------------------------------------------


class _OllamaAdapter(_ProviderAdapter):
    provider = AIProvider.OLLAMA

    def _url(self, path: str) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}{path}"

    # ----- Public methods -----------------------------------------------

    def generate_text(self, request: GenerationRequest) -> str:
        body: dict[str, Any] = {
            "model": request.model or self._settings.default_model,
            "prompt": self._combine_prompt(request),
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }
        if request.stop:
            body["options"]["stop"] = list(request.stop)
        for key, value in request.metadata.items():
            body[key] = value
        response = self._request("POST", self._url("/api/generate"), json=body)
        text = response.get("response")
        if not isinstance(text, str):
            raise AIResponseError(
                "Ollama response missing 'response'",
                body=json.dumps(response)[:512],
            )
        return text

    def generate_json(self, request: GenerationRequest) -> JSONObject:
        # Ask Ollama for a JSON-only response, then parse it.
        augmented = GenerationRequest(
            prompt=(
                f"{request.prompt}\n\n"
                "Respond with a single, valid JSON object and nothing else."
            ),
            system=request.system,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            metadata=request.metadata,
        )
        text = self.generate_text(augmented)
        return self._parse_json(text)

    def generate_image(self, request: ImageGenerationRequest) -> list[ImageResult]:
        # Some Ollama installs ship with image-capable models (e.g. the
        # ``llava`` family). We forward the prompt to ``/api/generate``
        # and treat any returned base64 image as the output.
        body: dict[str, Any] = {
            "model": request.model or "llava",
            "prompt": request.prompt,
            "stream": False,
        }
        response = self._request("POST", self._url("/api/generate"), json=body)
        # Ollama returns the image either under ``images`` (array of
        # base64 strings) or as a single ``image`` field.
        images: list[str] = []
        if isinstance(response.get("images"), list):
            images = [i for i in response["images"] if isinstance(i, str)]
        elif isinstance(response.get("image"), str):
            images = [response["image"]]
        if not images:
            raise AIResponseError(
                "Ollama image response had no images",
                body=json.dumps(response)[:512],
            )
        return [ImageResult(b64_json=img, mime_type="image/png") for img in images]

    def analyze_image(self, request: ImageAnalysisRequest) -> str:
        data, mime = self._encode_image(request.image)
        if mime == "image/url":
            raise AIValidationError(
                "Ollama analyze_image requires a local file or raw bytes, not a URL"
            )
        body: dict[str, Any] = {
            "model": request.model or "llava",
            "prompt": request.prompt,
            "stream": False,
            "images": [data],
        }
        response = self._request("POST", self._url("/api/generate"), json=body)
        text = response.get("response")
        if not isinstance(text, str):
            raise AIResponseError(
                "Ollama vision response missing 'response'",
                body=json.dumps(response)[:512],
            )
        return text

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        # Whisper-style transcription via Ollama uses /api/generate with
        # audio attached as base64.
        data, mime = self._encode_audio(request.audio)
        body: dict[str, Any] = {
            "model": request.model or "whisper",
            "stream": False,
            "audio": data,
        }
        if request.prompt:
            body["prompt"] = request.prompt
        response = self._request("POST", self._url("/api/generate"), json=body)
        text = response.get("response") or response.get("text")
        if not isinstance(text, str):
            raise AIResponseError(
                "Ollama transcription response missing text",
                body=json.dumps(response)[:512],
            )
        return AudioTranscriptionResult(
            text=text.strip(),
            language=request.language,
            raw=response,
        )

    @staticmethod
    def _encode_audio(audio: str | bytes) -> tuple[str, str]:
        if isinstance(audio, bytes):
            return base64.b64encode(audio).decode("ascii"), "audio/mpeg"
        if audio.startswith(("http://", "https://")):
            raise AIValidationError(
                "Ollama transcribe_audio requires a local file or raw bytes, not a URL"
            )
        if not os.path.isfile(audio):
            raise AIValidationError(f"Audio file not found: {audio}")
        with open(audio, "rb") as fh:
            data = fh.read()
        ext = os.path.splitext(audio)[1].lower()
        mime = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".flac": "audio/flac",
        }.get(ext, "application/octet-stream")
        return base64.b64encode(data).decode("ascii"), mime

    def health_check(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            self._request("GET", self._url("/api/tags"))
        except AIProviderError as exc:
            return HealthCheckResult(
                provider=self.provider,
                healthy=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                detail=str(exc),
                error=exc.__class__.__name__,
            )
        return HealthCheckResult(
            provider=self.provider,
            healthy=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    # ----- Helpers --------------------------------------------------------

    @staticmethod
    def _combine_prompt(request: GenerationRequest) -> str:
        if request.system:
            return f"<<SYS>>\n{request.system}\n<</SYS>>\n\n{request.prompt}"
        return request.prompt


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------


_AdapterFactory = Callable[[AIClientSettings, _SupportsRequests], _ProviderAdapter]


_ADAPTERS: dict[AIProvider, _AdapterFactory] = {
    AIProvider.OPENAI: _OpenAIAdapter,
    AIProvider.OPENROUTER: _OpenRouterAdapter,
    AIProvider.GEMINI: _GeminiAdapter,
    AIProvider.ANTHROPIC: _AnthropicAdapter,
    AIProvider.OLLAMA: _OllamaAdapter,
}


class AIClient:
    """High-level facade that delegates to the configured provider.

    Example
    -------
    >>> client = AIClient()  # uses environment variables
    >>> text = client.generate_text(GenerationRequest(prompt="Hello!"))
    >>> print(text)

    Parameters
    ----------
    settings
        Optional :class:`AIClientSettings`. When omitted, the
        environment is consulted via :meth:`AIClientSettings.from_env`.
    transport
        Optional HTTP transport. Must implement the same interface as
        :class:`requests.Session`. Defaults to a fresh
        :class:`requests.Session` instance. Tests can pass a stub.
    logger
        Optional :class:`logging.Logger`. Defaults to a logger named
        after this module.
    """

    def __init__(
        self,
        settings: AIClientSettings | None = None,
        *,
        transport: _SupportsRequests | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings or AIClientSettings.from_env()
        self._transport: _SupportsRequests = transport or Session()
        self._log = logger or logging.getLogger(__name__)
        self._configure_logging()
        self._adapters: dict[AIProvider, _ProviderAdapter] = {}
        self._log.info(
            "AIClient initialised (provider=%s model=%s)",
            self._settings.default_provider.value,
            self._settings.default_model,
        )

    # ----- Logging -------------------------------------------------------

    def _configure_logging(self) -> None:
        level_name = self._settings.log_level.upper()
        level = logging.getLevelName(level_name)
        if not isinstance(level, int):
            level = logging.INFO
        self._log.setLevel(level)
        if not self._log.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )
            self._log.addHandler(handler)

    # ----- Adapter access ------------------------------------------------

    def _adapter(self, provider: AIProvider | None = None) -> _ProviderAdapter:
        target = AIProvider.coerce(provider or self._settings.default_provider)
        adapter = self._adapters.get(target)
        if adapter is None:
            factory = _ADAPTERS.get(target)
            if factory is None:
                raise AIValidationError(f"No adapter registered for {target}")
            adapter = factory(self._settings, self._transport)
            self._adapters[target] = adapter
        return adapter

    # ----- Public API ----------------------------------------------------

    def generate_text(
        self,
        request: GenerationRequest,
        *,
        provider: str | AIProvider | None = None,
    ) -> str:
        """Generate a plain-text completion.

        Parameters
        ----------
        request
            A populated :class:`GenerationRequest`. ``request.prompt``
            is required; all other fields have sensible defaults.
        provider
            Optional provider override. When ``None``, the client's
            ``default_provider`` is used.

        Returns
        -------
        str
            The model's text response.
        """
        self._validate_generation(request)
        self._log.info(
            "generate_text provider=%s model=%s prompt_len=%d",
            (provider or self._settings.default_provider.value),
            request.model or self._settings.default_model,
            len(request.prompt),
        )
        return self._adapter(provider).generate_text(request)

    def generate_json(
        self,
        request: GenerationRequest,
        *,
        provider: str | AIProvider | None = None,
    ) -> JSONObject:
        """Generate a JSON object completion.

        The provider is asked to return JSON; the response is parsed
        and validated as a ``dict`` before being returned.

        Raises
        ------
        AIResponseError
            If the model output cannot be parsed as a JSON object.
        """
        self._validate_generation(request)
        self._log.info(
            "generate_json provider=%s model=%s prompt_len=%d",
            (provider or self._settings.default_provider.value),
            request.model or self._settings.default_model,
            len(request.prompt),
        )
        return self._adapter(provider).generate_json(request)

    def generate_image(
        self,
        request: ImageGenerationRequest,
        *,
        provider: str | AIProvider | None = None,
    ) -> list[ImageResult]:
        """Generate one or more images from a text prompt.

        Returns
        -------
        list[ImageResult]
            A list of generated images, in the same order the provider
            returned them. The list always contains at least one item
            on success.
        """
        self._validate_image_request(request)
        target = AIProvider.coerce(provider or self._settings.default_provider)
        self._log.info(
            "generate_image provider=%s model=%s prompt_len=%d",
            target.value,
            request.model or "default",
            len(request.prompt),
        )
        return self._adapter(target).generate_image(request)

    def analyze_image(
        self,
        request: ImageAnalysisRequest,
        *,
        provider: str | AIProvider | None = None,
    ) -> str:
        """Analyse an image and return a textual description."""
        if not request.prompt:
            raise AIValidationError("analyze_image requires a non-empty prompt")
        if not request.image:
            raise AIValidationError("analyze_image requires image data")
        target = AIProvider.coerce(provider or self._settings.default_provider)
        self._log.info(
            "analyze_image provider=%s model=%s",
            target.value,
            request.model or self._settings.default_model,
        )
        return self._adapter(target).analyze_image(request)

    def transcribe_audio(
        self,
        request: AudioTranscriptionRequest,
        *,
        provider: str | AIProvider | None = None,
    ) -> AudioTranscriptionResult:
        """Transcribe audio into text."""
        if not request.audio:
            raise AIValidationError("transcribe_audio requires audio data")
        target = AIProvider.coerce(provider or self._settings.default_provider)
        self._log.info(
            "transcribe_audio provider=%s model=%s",
            target.value,
            request.model or "default",
        )
        return self._adapter(target).transcribe_audio(request)

    def health_check(
        self,
        provider: str | AIProvider | None = None,
    ) -> HealthCheckResult:
        """Run a lightweight health probe against one provider.

        If ``provider`` is ``None``, every configured provider is
        probed and the result is summarised; the returned
        :class:`HealthCheckResult` has ``healthy`` set to ``True`` only
        when **all** providers are healthy.
        """
        if provider is None:
            return self._health_check_all()
        return self._adapter(provider).health_check()

    def close(self) -> None:
        """Close the underlying HTTP transport (if it supports it)."""
        close = getattr(self._transport, "close", None)
        if callable(close):
            close()

    # ----- Context-manager support --------------------------------------

    def __enter__(self) -> "AIClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # ----- Internal helpers ---------------------------------------------

    def _validate_generation(self, request: GenerationRequest) -> None:
        if not request.prompt or not request.prompt.strip():
            raise AIValidationError("GenerationRequest.prompt must be a non-empty string")
        if not 0.0 <= request.temperature <= 2.0:
            raise AIValidationError(
                f"temperature must be in [0, 2], got {request.temperature}"
            )
        if request.max_tokens <= 0:
            raise AIValidationError("max_tokens must be positive")
        if not 0.0 <= request.top_p <= 1.0:
            raise AIValidationError(f"top_p must be in [0, 1], got {request.top_p}")

    def _validate_image_request(self, request: ImageGenerationRequest) -> None:
        if not request.prompt or not request.prompt.strip():
            raise AIValidationError(
                "ImageGenerationRequest.prompt must be a non-empty string"
            )
        if request.n <= 0:
            raise AIValidationError("n must be positive")

    def _health_check_all(self) -> HealthCheckResult:
        results: list[HealthCheckResult] = []
        for provider in AIProvider:
            try:
                results.append(self._adapter(provider).health_check())
            except AIProviderError as exc:
                results.append(
                    HealthCheckResult(
                        provider=provider,
                        healthy=False,
                        latency_ms=None,
                        detail=str(exc),
                        error=exc.__class__.__name__,
                    )
                )
        healthy = all(r.healthy for r in results)
        primary = results[0] if results else None
        return HealthCheckResult(
            provider=primary.provider if primary else self._settings.default_provider,
            healthy=healthy,
            latency_ms=primary.latency_ms if primary else None,
            detail=", ".join(
                f"{r.provider.value}={'ok' if r.healthy else 'fail'}" for r in results
            ),
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def configure_logging(level: str | int = "INFO") -> None:
    """Convenience helper to enable logging for the AI client.

    Parameters
    ----------
    level
        Either a level name (``"DEBUG"``) or a numeric level
        (``logging.DEBUG``).
    """
    logger = logging.getLogger("app.brain.ai_client")
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
    if not isinstance(level, int):  # pragma: no cover - defensive
        level = logging.INFO
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        )
        logger.addHandler(handler)
