"""Provider-independent rate, concurrency, retry, timeout, and cache control."""

from __future__ import annotations

import asyncio
import math
import random
import time
from collections.abc import Awaitable, Callable, Hashable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import TypeVar, cast

from aiolimiter import AsyncLimiter
from cachetools import TTLCache

from .errors import TransientRequestError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RequestGovernorConfig:
    """Shared request-control defaults and their valid boundaries."""

    requests_per_minute: int = 30
    max_concurrency: int = 1
    timeout_seconds: float = 30
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 2
    cache_ttl_seconds: float = 60

    def __post_init__(self) -> None:
        for name in ("requests_per_minute", "max_concurrency", "retry_max_attempts"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name, minimum, inclusive in (
            ("timeout_seconds", 0, False),
            ("retry_base_delay_seconds", 0, True),
            ("cache_ttl_seconds", 0, True),
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < minimum
                or (not inclusive and value == minimum)
            ):
                comparator = ">=" if inclusive else ">"
                raise ValueError(f"{name} must be a finite number {comparator} {minimum}")


class RequestGovernor:
    """Execute asynchronous operations under one shared control policy."""

    def __init__(
        self,
        config: RequestGovernorConfig | None = None,
        *,
        _limiter: AbstractAsyncContextManager[object] | None = None,
        _sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
        _clock: Callable[[], float] = time.monotonic,
        _jitter: Callable[[float], float] | None = None,
    ) -> None:
        self.config = config or RequestGovernorConfig()
        self._limiter = _limiter or AsyncLimiter(self.config.requests_per_minute, 60)
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._sleep = _sleep
        self._jitter = _jitter or (lambda delay: random.uniform(0, delay * 0.1))
        self._cache: TTLCache[Hashable, object] | None = None
        if self.config.cache_ttl_seconds > 0:
            self._cache = TTLCache(maxsize=1024, ttl=self.config.cache_ttl_seconds, timer=_clock)
        self._cache_lock = asyncio.Lock()

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        cache_key: Hashable | None = None,
        retry: bool = True,
    ) -> T:
        """Run an operation; only explicit keys opt into successful-result caching."""
        if cache_key is not None and self._cache is not None:
            async with self._cache_lock:
                try:
                    return cast(T, self._cache[cache_key])
                except KeyError:
                    pass

        max_attempts = self.config.retry_max_attempts if retry else 1
        for attempt in range(1, max_attempts + 1):
            try:
                async with self._limiter:
                    pass
                async with self._semaphore:
                    async with asyncio.timeout(self.config.timeout_seconds):
                        result = await operation()
            except (TimeoutError, ConnectionResetError, TransientRequestError):
                if attempt == max_attempts:
                    raise
                delay = self.config.retry_base_delay_seconds * (2 ** (attempt - 1))
                await self._sleep(delay + self._jitter(delay))
            else:
                if cache_key is not None and self._cache is not None:
                    async with self._cache_lock:
                        self._cache[cache_key] = result
                return result
        raise AssertionError("request loop must return or raise")
