"""LLM call retry utilities with exponential backoff.

Provides:
- ``is_retryable(exc)`` — classify whether an exception is transient
- ``with_retry()`` — async decorator that retries on transient failures
"""

import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# HTTP status codes considered transient (worth retrying)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def is_retryable(exc: Exception) -> bool:
    """Determine if an exception is transient and worth retrying.

    Retryable: rate limits (429), server errors (5xx), timeouts.
    Non-retryable: auth errors (401/403), bad requests (400), etc.
    """
    # Timeout errors are always retryable
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True

    # google-genai SDK errors
    try:
        from google.genai.errors import APIError, ServerError
    except ImportError:
        return False

    if isinstance(exc, ServerError):
        return True
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        if code and code in RETRYABLE_STATUS_CODES:
            return True

    return False


def with_retry(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float = 30.0,
    timeout: float | None = None,
):
    """Decorator: wrap an async function with exponential backoff retry.

    Only retries on transient errors (429, 5xx, timeouts).
    Non-retryable errors propagate immediately.

    Args:
        max_attempts: Maximum number of attempts (default from settings).
        base_delay: Initial delay in seconds before first retry (default from settings).
        max_delay: Maximum delay cap in seconds.
        timeout: Per-call timeout in seconds (default from settings).
    """
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            from app.config import settings

            _max = max_attempts or settings.llm_max_retries
            _delay = base_delay or settings.llm_retry_base_delay
            _timeout = timeout or settings.llm_timeout

            last_exc: Exception | None = None
            for attempt in range(_max):
                try:
                    return await asyncio.wait_for(
                        fn(*args, **kwargs),
                        timeout=_timeout,
                    )
                except Exception as e:
                    last_exc = e
                    if not is_retryable(e) or attempt == _max - 1:
                        raise
                    delay = min(_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        "LLM call %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                        fn.__name__, attempt + 1, _max, e, delay,
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]  # unreachable but satisfies type checker
        return wrapper
    return decorator
