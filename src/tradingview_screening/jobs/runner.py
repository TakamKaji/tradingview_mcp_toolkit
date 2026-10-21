"""Execute one named Job through the existing Screening and Watchlist APIs."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from tradingview_screening.common.config import definition_path
from tradingview_screening.common.errors import AppError, ConfigError, TransientRequestError
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.screening.engine import run_screening
from tradingview_screening.screening.results import TOKYO, save_result, write_json_result
from tradingview_screening.screening.watchlist_sync import sync_screening_watchlist

from .builtin import BUILTINS, validate_builtin_job
from .loader import list_job_names, load_job_by_name, validate_job_screening_reference
from .schema import JobDefinition


def _lock_path(project_root: Path, name: str) -> Path:
    definition_path(project_root / "jobs", name, project_root=project_root)
    local = project_root / ".local"
    folder = local / "job_locks"
    try:
        root = project_root.resolve()
        if (
            local.is_symlink() or local.resolve() != root / ".local"
            or folder.is_symlink() or folder.resolve() != root / ".local" / "job_locks"
        ):
            raise AppError("JOB_LOCK_ERROR", "Job lock path is unsafe")
        folder.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
        path = folder / f"{digest}.lock"
        if path.is_symlink() or path.resolve() != folder.resolve() / path.name:
            raise AppError("JOB_LOCK_ERROR", "Job lock path is unsafe")
        return path
    except AppError:
        raise
    except (OSError, RuntimeError) as exc:
        raise AppError("JOB_LOCK_ERROR", "Cannot prepare Job lock") from exc


def _envelope(name: str, job: JobDefinition | None, started: float) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "status": "success",
        "operation": "job",
        "name": name,
        "executedAt": datetime.now(TOKYO).isoformat(),
        "task": (
            {"type": job.task.type, "definition": job.task.definition} if job is not None else None
        ),
        "metadata": {
            "skipped": False,
            "durationMs": 0,
            "saved": False,
            "resultPath": None,
        },
        "screening": None,
        "builtin": None,
        "watchlistSync": None,
        "errors": [],
    }


def _finish(payload: dict[str, Any], started: float) -> dict[str, Any]:
    payload["metadata"]["durationMs"] = round((time.monotonic() - started) * 1000)
    return payload


def failed_job(name: str, error: AppError | ConfigError, *, started: float | None = None) -> dict[str, Any]:
    """Build the same Job Envelope for a load/validation failure at the CLI boundary."""
    began = time.monotonic() if started is None else started
    payload = _envelope(name, None, began)
    payload["status"] = "failed"
    payload["errors"] = [{"code": error.code, "message": error.message}]
    return _finish(payload, began)


def job_exit_code(payload: dict[str, Any]) -> int:
    codes = {item["code"] for item in payload["errors"]}
    if "AUTH_REQUIRED" in codes:
        return 3
    if payload["status"] in {"success", "partial"}:
        return 0
    if any(code.startswith("CONFIG_") or code == "CLI_USAGE_ERROR" for code in codes):
        return 2
    return 1


def list_jobs(project_root: Path) -> dict[str, Any]:
    """Validate every local Job and referenced Screening before emitting a list."""
    jobs: list[dict[str, Any]] = []
    for name in list_job_names(project_root):
        job = load_job_by_name(name, project_root)
        if job.task.type == "screening":
            validate_job_screening_reference(job, project_root)
        else:
            try:
                validate_builtin_job(job)
            except AppError as exc:
                if exc.code == "JOB_TASK_UNAVAILABLE":
                    raise ConfigError(
                        "CONFIG_REFERENCE_NOT_FOUND",
                        "Referenced builtin is unavailable",
                        "task.definition",
                    ) from exc
                raise
        jobs.append({
            "name": job.name,
            "enabled": job.enabled,
            "task": {"type": job.task.type, "definition": job.task.definition},
            "schedule": {
                "type": job.schedule.type,
                "time": job.schedule.time,
                "timezone": job.schedule.timezone,
            },
            "output": {"save": job.output.save, "watchlistSync": job.output.watchlistSync},
        })
    return {"schemaVersion": 1, "status": "success", "operation": "jobs_list", "jobs": jobs}


def _record_error(payload: dict[str, Any], error: AppError | ConfigError) -> None:
    payload["status"] = "failed"
    payload["errors"].append({"code": error.code, "message": error.message})


def _screening_status(payload: dict[str, Any], result: dict[str, Any]) -> bool:
    """Transfer only normalized Screening envelopes; signal whether sync is safe."""
    if (
        not isinstance(result, dict)
        or result.get("operation") != "screening"
        or result.get("status") not in {"success", "partial", "failed"}
        or not isinstance(result.get("errors"), list)
    ):
        raise AppError("JOB_SCREENING_INVALID", "Screening result is invalid")
    payload["screening"] = result
    if result["status"] == "failed":
        payload["status"] = "failed"
        payload["errors"] = result["errors"] or [
            {"code": "JOB_SCREENING_FAILED", "message": "Screening failed"}
        ]
        return False
    if result["status"] == "partial":
        payload["status"] = "partial"
        payload["errors"] = result["errors"]
        return False
    return True


async def run_job(name: str, project_root: Path) -> dict[str, Any]:
    """Run one Job; an already-running Job returns a successful skip immediately."""
    started = time.monotonic()
    job = load_job_by_name(name, project_root)
    payload = _envelope(name, job, started)
    path = _lock_path(project_root, name)
    lock = FileLock(path, thread_local=False)
    try:
        lock.acquire(timeout=0)
    except Timeout:
        payload["metadata"].update({"skipped": True, "reason": "already_running"})
        return _finish(payload, started)
    except OSError as exc:
        raise AppError("JOB_LOCK_ERROR", "Cannot acquire Job lock") from exc
    try:
        if job.task.type == "builtin":
            validate_builtin_job(job)
            builtin = BUILTINS[job.task.definition]
            async with TradingViewClient() as client:
                result = await builtin(client)
            if (
                not isinstance(result, dict)
                or result.get("operation") != "us_sector_summary"
                or result.get("status") != "success"
                or result.get("name") != job.task.definition
            ):
                raise AppError("JOB_BUILTIN_INVALID", "Builtin result is invalid")
            payload["builtin"] = result
            if job.output.save:
                try:
                    retrieved_at = datetime.fromisoformat(result["retrievedAt"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise AppError("JOB_BUILTIN_INVALID", "Builtin retrieval time is invalid") from exc
                saved_path = write_json_result(
                    result, name=job.name, executed_at=retrieved_at, project_root=project_root,
                )
                payload["metadata"]["saved"] = True
                payload["metadata"]["resultPath"] = saved_path.relative_to(project_root).as_posix()
            return _finish(payload, started)
        screening = validate_job_screening_reference(job, project_root)
        if screening is None:
            raise AppError("JOB_TASK_UNAVAILABLE", "Job task is unavailable")
        async with TradingViewClient() as client:
            result = await run_screening(screening, client)
            sync_safe = _screening_status(payload, result)
            if payload["status"] == "failed":
                if job.output.watchlistSync:
                    payload["watchlistSync"] = {
                        "status": "skipped", "reason": "screening_not_successful"
                    }
                return _finish(payload, started)
            if job.output.save:
                saved_path = save_result(result, project_root)
                payload["metadata"]["saved"] = True
                payload["metadata"]["resultPath"] = saved_path.relative_to(project_root).as_posix()
            if job.output.watchlistSync:
                if not sync_safe:
                    payload["watchlistSync"] = {
                        "status": "skipped", "reason": "screening_not_successful"
                    }
                else:
                    sync = await sync_screening_watchlist(screening, result, client, project_root)
                    payload["watchlistSync"] = sync
                    if sync.get("status") == "failed":
                        payload["status"] = "failed"
                        payload["errors"].extend(sync.get("errors", []))
                    elif sync.get("status") == "partial":
                        payload["status"] = "partial"
                        payload["errors"].extend(sync.get("errors", []))
                    elif sync.get("status") != "success":
                        raise AppError("JOB_WATCHLIST_INVALID", "Watchlist sync result is invalid")
    except (ConfigError, AppError) as exc:
        _record_error(payload, exc)
    except (TimeoutError, ConnectionResetError, TransientRequestError):
        _record_error(payload, AppError("MCP_CONNECTION_ERROR", "Job provider operation failed"))
    except Exception:  # noqa: BLE001 - never expose SDK, OS, or credential exception text.
        _record_error(payload, AppError("JOB_EXECUTION_ERROR", "Job execution failed"))
    finally:
        try:
            lock.release()
        except OSError:
            _record_error(payload, AppError("JOB_LOCK_ERROR", "Cannot release Job lock"))
    return _finish(payload, started)
