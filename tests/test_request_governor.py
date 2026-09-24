from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from tradingview_screening.common.errors import TransientRequestError
from tradingview_screening.common.request_governor import RequestGovernor, RequestGovernorConfig


class CountingLimiter:
    def __init__(self) -> None:
        self.entries = 0

    async def __aenter__(self) -> None:
        self.entries += 1

    async def __aexit__(self, *_args: object) -> None:
        pass


def test_config_defaults_and_valid_boundaries() -> None:
    assert asdict(RequestGovernorConfig()) == {
        "requests_per_minute": 30,
        "max_concurrency": 1,
        "timeout_seconds": 30,
        "retry_max_attempts": 3,
        "retry_base_delay_seconds": 2,
        "cache_ttl_seconds": 60,
    }
    config = RequestGovernorConfig(
        requests_per_minute=1,
        max_concurrency=2,
        timeout_seconds=0.1,
        retry_max_attempts=1,
        retry_base_delay_seconds=0,
        cache_ttl_seconds=0,
    )
    assert config.max_concurrency == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requests_per_minute", 0),
        ("requests_per_minute", -1),
        ("max_concurrency", 0),
        ("max_concurrency", -1),
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("retry_max_attempts", 0),
        ("retry_max_attempts", -1),
        ("retry_base_delay_seconds", -0.1),
        ("cache_ttl_seconds", -1),
        ("requests_per_minute", 1.5),
        ("max_concurrency", True),
        ("retry_max_attempts", False),
        ("timeout_seconds", True),
        ("retry_base_delay_seconds", float("nan")),
        ("cache_ttl_seconds", float("inf")),
        ("timeout_seconds", float("-inf")),
        ("cache_ttl_seconds", float("nan")),
        ("retry_base_delay_seconds", float("-inf")),
    ],
)
def test_config_rejects_invalid_values(field: str, value: Any) -> None:
    with pytest.raises(ValueError, match=field):
        RequestGovernorConfig(**{field: value})


def test_basic_result_and_unclassified_error(capsys: pytest.CaptureFixture[str]) -> None:
    async def scenario() -> None:
        governor = RequestGovernor()

        async def operation() -> list[int]:
            return [1, 2]

        assert await governor.execute(operation) == [1, 2]

        calls = 0

        async def fail() -> None:
            nonlocal calls
            calls += 1
            raise RuntimeError("original")

        with pytest.raises(RuntimeError, match="original"):
            await governor.execute(fail)
        assert calls == 1

    asyncio.run(scenario())
    assert capsys.readouterr() == ("", "")


def test_limiter_uses_configured_rate() -> None:
    default = RequestGovernor()
    changed = RequestGovernor(RequestGovernorConfig(requests_per_minute=7))
    assert default._limiter.max_rate == 30
    assert default._limiter.time_period == 60
    assert changed._limiter.max_rate == 7
    assert changed._limiter.time_period == 60


@pytest.mark.parametrize("max_concurrency", [1, 2])
def test_concurrency_limit(max_concurrency: int) -> None:
    async def scenario() -> None:
        governor = RequestGovernor(RequestGovernorConfig(max_concurrency=max_concurrency))
        active = 0
        peak = 0
        started = asyncio.Event()
        release = asyncio.Event()

        async def operation() -> None:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == max_concurrency:
                started.set()
            await release.wait()
            active -= 1

        tasks = [asyncio.create_task(governor.execute(operation)) for _ in range(3)]
        await asyncio.wait_for(started.wait(), 1)
        await asyncio.sleep(0)
        assert peak == max_concurrency
        release.set()
        await asyncio.gather(*tasks)
        assert peak == max_concurrency

    asyncio.run(scenario())


def test_retry_classification_attempt_count_limiter_and_backoff() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        delays: list[float] = []

        async def fake_sleep(delay: float) -> None:
            delays.append(delay)

        governor = RequestGovernor(
            _limiter=limiter,
            _sleep=fake_sleep,
            _jitter=lambda delay: delay * 0.05,
        )
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionResetError("reset")
            if calls == 2:
                raise TransientRequestError("temporary")
            return "done"

        assert await governor.execute(operation) == "done"
        assert calls == limiter.entries == 3
        assert delays == [2.1, 4.2]

    asyncio.run(scenario())


class _ValidationModel(BaseModel):
    value: int


@pytest.mark.parametrize(
    "error",
    [
        ValueError("arg"),
        PermissionError("denied"),
        RuntimeError("unknown"),
        pytest.param(
            None,
            id="pydantic-validation-error",
        ),
    ],
)
def test_nonretryable_errors_run_once(error: Exception) -> None:
    if error is None:
        with pytest.raises(ValidationError) as caught:
            _ValidationModel(value="not-an-int")
        error = caught.value

    async def scenario() -> None:
        limiter = CountingLimiter()
        calls = 0

        async def operation() -> None:
            nonlocal calls
            calls += 1
            raise error

        governor = RequestGovernor(_limiter=limiter)
        with pytest.raises(type(error)) as caught:
            await governor.execute(operation)
        assert caught.value is error
        assert calls == limiter.entries == 1

    asyncio.run(scenario())


def test_limiter_wait_does_not_hold_concurrency_slot() -> None:
    class FirstEntryWaits(CountingLimiter):
        def __init__(self) -> None:
            super().__init__()
            self.waiting = asyncio.Event()
            self.release = asyncio.Event()

        async def __aenter__(self) -> None:
            await super().__aenter__()
            if self.entries == 1:
                self.waiting.set()
                await self.release.wait()

    async def scenario() -> None:
        limiter = FirstEntryWaits()
        governor = RequestGovernor(_limiter=limiter)

        async def operation() -> str:
            return "ok"

        first = asyncio.create_task(governor.execute(operation))
        await limiter.waiting.wait()
        assert await asyncio.wait_for(governor.execute(operation), 1) == "ok"
        limiter.release.set()
        assert await first == "ok"
        assert limiter.entries == 2

    asyncio.run(scenario())


def test_retry_false_and_max_attempts() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        calls = 0

        async def fail() -> None:
            nonlocal calls
            calls += 1
            raise TransientRequestError("temporary")

        governor = RequestGovernor(
            RequestGovernorConfig(retry_max_attempts=2),
            _limiter=limiter,
            _sleep=lambda _delay: asyncio.sleep(0),
        )
        with pytest.raises(TransientRequestError):
            await governor.execute(fail, retry=False)
        assert calls == limiter.entries == 1
        with pytest.raises(TransientRequestError):
            await governor.execute(fail)
        assert calls == limiter.entries == 3

    asyncio.run(scenario())


def test_retry_false_timeout_runs_once_without_backoff() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        delays: list[float] = []
        calls = 0

        async def fake_sleep(delay: float) -> None:
            delays.append(delay)

        governor = RequestGovernor(
            RequestGovernorConfig(timeout_seconds=0.01),
            _limiter=limiter,
            _sleep=fake_sleep,
        )

        async def operation() -> None:
            nonlocal calls
            calls += 1
            await asyncio.Event().wait()

        with pytest.raises(TimeoutError):
            await governor.execute(operation, retry=False)

        assert calls == 1
        assert limiter.entries == 1
        assert delays == []

    asyncio.run(scenario())


def test_backoff_releases_slot_before_next_attempt() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        holder: dict[str, RequestGovernor] = {}
        calls = 0

        async def second() -> str:
            return "second"

        async def fake_sleep(_delay: float) -> None:
            assert await asyncio.wait_for(holder["governor"].execute(second, retry=False), 1) == "second"

        governor = RequestGovernor(_limiter=limiter, _sleep=fake_sleep)
        holder["governor"] = governor

        async def first() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionResetError("reset")
            return "first"

        assert await governor.execute(first) == "first"
        assert limiter.entries == 3

    asyncio.run(scenario())


def test_timeout_retries_and_releases_slot() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        governor = RequestGovernor(
            RequestGovernorConfig(timeout_seconds=0.01, retry_base_delay_seconds=0),
            _limiter=limiter,
            _sleep=lambda _delay: asyncio.sleep(0),
        )
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                await asyncio.Event().wait()
            return "recovered"

        assert await asyncio.wait_for(governor.execute(operation), 1) == "recovered"
        assert calls == limiter.entries == 2

        async def fail() -> None:
            raise RuntimeError("failure")

        with pytest.raises(RuntimeError):
            await governor.execute(fail, retry=False)
        assert await governor.execute(operation, retry=False) == "recovered"

    asyncio.run(scenario())


def test_cancellation_releases_slot_and_propagates() -> None:
    async def scenario() -> None:
        governor = RequestGovernor()
        started = asyncio.Event()

        async def blocked() -> None:
            started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(governor.execute(blocked))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        async def next_operation() -> int:
            return 42

        assert await asyncio.wait_for(governor.execute(next_operation), 1) == 42

    asyncio.run(scenario())


def test_cache_hit_miss_key_expiry_and_no_key() -> None:
    async def scenario() -> None:
        now = [0.0]
        limiter = CountingLimiter()
        governor = RequestGovernor(_limiter=limiter, _clock=lambda: now[0])
        calls = 0

        async def operation() -> object:
            nonlocal calls
            calls += 1
            return None if calls == 1 else calls

        assert await governor.execute(operation, cache_key="a") is None
        assert await governor.execute(operation, cache_key="a") is None
        assert calls == limiter.entries == 1
        assert await governor.execute(operation, cache_key="b") == 2
        assert await governor.execute(operation) == 3
        assert await governor.execute(operation) == 4
        now[0] = 60.0
        assert await governor.execute(operation, cache_key="a") == 5
        assert calls == limiter.entries == 5

    asyncio.run(scenario())


def test_cache_hit_does_not_wait_for_occupied_slot() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        governor = RequestGovernor(_limiter=limiter)

        async def cached() -> str:
            return "cached"

        assert await governor.execute(cached, cache_key="key") == "cached"
        started = asyncio.Event()
        release = asyncio.Event()

        async def blocked() -> None:
            started.set()
            await release.wait()

        task = asyncio.create_task(governor.execute(blocked))
        await started.wait()
        assert await asyncio.wait_for(governor.execute(cached, cache_key="key"), 1) == "cached"
        assert limiter.entries == 2
        release.set()
        await task

    asyncio.run(scenario())


def test_cache_only_success_and_ttl_zero() -> None:
    async def scenario() -> None:
        limiter = CountingLimiter()
        governor = RequestGovernor(
            RequestGovernorConfig(cache_ttl_seconds=0), _limiter=limiter
        )
        calls = 0

        async def operation() -> int:
            nonlocal calls
            calls += 1
            return calls

        assert await governor.execute(operation, cache_key="a") == 1
        assert await governor.execute(operation, cache_key="a") == 2

        cached = RequestGovernor(_limiter=limiter)
        errors = 0

        async def sometimes_fails() -> int:
            nonlocal errors
            errors += 1
            if errors == 1:
                raise ValueError("bad")
            return errors

        with pytest.raises(ValueError):
            await cached.execute(sometimes_fails, cache_key="error")
        assert await cached.execute(sometimes_fails, cache_key="error") == 2
        assert await cached.execute(sometimes_fails, cache_key="error") == 2
        assert errors == 2
        assert limiter.entries == 4

    asyncio.run(scenario())


def test_timeout_is_not_cached() -> None:
    async def scenario() -> None:
        governor = RequestGovernor(RequestGovernorConfig(timeout_seconds=0.01))
        calls = 0

        async def operation() -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                await asyncio.Event().wait()
            return calls

        with pytest.raises(TimeoutError):
            await governor.execute(operation, cache_key="key", retry=False)
        assert await governor.execute(operation, cache_key="key", retry=False) == 2
        assert await governor.execute(operation, cache_key="key", retry=False) == 2
        assert calls == 2

    asyncio.run(scenario())
