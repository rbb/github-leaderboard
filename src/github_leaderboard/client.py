"""GhApi wrapper with exponential backoff for rate-limit handling."""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from ghapi.all import GhApi

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_BACKOFF_DELAYS = [1, 2, 4, 8, 16]


class RateLimitExhaustedError(Exception):
    pass


def retry_with_backoff(func: F) -> F:
    """Decorator: retry on GitHub rate-limit (403/429) with exponential backoff."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for attempt, delay in enumerate(_BACKOFF_DELAYS, start=1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                msg = str(exc).lower()
                # Detect rate-limit responses
                is_rate_limit = (
                    "rate limit" in msg
                    or "rate_limit" in msg
                    or getattr(exc, "status", 0) in (429, 403)
                )
                if not is_rate_limit:
                    raise
                last_exc = exc
                logger.warning(
                    "GitHub rate limit hit (attempt %d/%d); retrying in %ds — %s",
                    attempt,
                    len(_BACKOFF_DELAYS),
                    delay,
                    exc,
                )
                time.sleep(delay)
        raise RateLimitExhaustedError(
            f"GitHub REST API rate limit retries exhausted after {len(_BACKOFF_DELAYS)} attempts."
        ) from last_exc

    return wrapper  # type: ignore[return-value]


def make_api(token: str) -> GhApi:
    return GhApi(token=token)
