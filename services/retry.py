"""Shared, deadline-bounded Gemini retries; never log provider payloads."""
import logging
import random
import time
from contextlib import contextmanager
from contextvars import ContextVar
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import httpx
from google.genai import errors, types

logger = logging.getLogger(__name__)
_deadline = ContextVar('gemini_deadline', default=None)


@contextmanager
def request_budget(seconds=180):
    token = _deadline.set(time.monotonic() + seconds)
    try:
        yield
    finally:
        _deadline.reset(token)


def http_options(timeout_ms):
    # Disable nested SDK retries: this module owns attempts and delays.
    return types.HttpOptions(timeout=timeout_ms, retry_options=types.HttpRetryOptions(attempts=1))


def retry_delay(exc):
    """Honor Retry-After and Google's structured RetryInfo without logging them."""
    delays = [0.0]
    response = getattr(exc, 'response', None)
    header = getattr(response, 'headers', {}).get('Retry-After') if response is not None else None
    if header:
        try:
            delays.append(float(header))
        except ValueError:
            try:
                delays.append((parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError):
                pass
    payload = getattr(exc, 'details', {}) or {}
    details = payload.get('error', payload).get('details', []) if isinstance(payload, dict) else []
    for item in details:
        if isinstance(item, dict) and str(item.get('@type', '')).endswith('RetryInfo'):
            try:
                delays.append(float(str(item.get('retryDelay', '0s')).removesuffix('s')))
            except ValueError:
                pass
    return max(delays)


def call_with_retry(operation, *, label, max_attempts=4, deadline=None):
    """Operation receives the remaining per-attempt timeout in milliseconds."""
    deadline = min(d for d in (deadline, _deadline.get(), time.monotonic() + 180) if d is not None)
    for attempt in range(max_attempts):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('AI request deadline exceeded')
        try:
            return operation(max(1, min(40000, int(remaining * 1000))))
        except (errors.APIError, httpx.TransportError, TimeoutError, ConnectionError) as exc:
            code = getattr(exc, 'code', None)
            if isinstance(exc, errors.APIError) and code not in {408, 429, 500, 502, 503, 504}:
                raise
            delay = max(min(2 ** attempt, 30) + random.uniform(0, 1), retry_delay(exc))
            if attempt + 1 >= max_attempts or delay + 1 >= deadline - time.monotonic():
                raise
            logger.warning('AI retry stage=%s attempt=%d code=%s delay_seconds=%.1f', label, attempt + 1, code, delay)
            time.sleep(delay)
