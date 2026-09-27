"""Windows Task Scheduler adapter through a fixed PowerShell/COM bridge."""

from __future__ import annotations

import base64
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from tradingview_screening.common.config import definition_path
from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.screening.results import TOKYO

from .builtin import BUILTINS
from .loader import list_job_names, load_job_by_name, validate_job_screening_reference
from .schema import JobDefinition

TASK_PREFIX = "TradingViewMcpSupport__"
_UNSAFE_ACTION_PATH = re.compile(r'["%!^&|<>\r\n]')
_BRIDGE_TIMEOUT_SECONDS = 30

_ACTION_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
$payload = ConvertFrom-Json -InputObject (
    [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_payload}'))
)
$start = New-Object Diagnostics.ProcessStartInfo
$start.FileName = [IO.Path]::Combine($env:SystemRoot, 'System32\cmd.exe')
$start.Arguments = '/d /s /c ""' + $payload.appBat + '" run ' + $payload.name + '"'
$start.WorkingDirectory = $payload.projectRoot
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$process = [Diagnostics.Process]::Start($start)
$process.WaitForExit()
exit $process.ExitCode
} catch {
    exit 1
}
"""

# This is fixed code. All repository paths, task names, and times arrive as JSON
# on stdin; none is inserted into PowerShell source or passed to a shell.
_COM_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    $payload = ConvertFrom-Json -InputObject ([Console]::In.ReadToEnd())
    $service = New-Object -ComObject 'Schedule.Service'
    $service.Connect()
    $folder = $service.GetFolder('\')
    $collection = $folder.GetTasks(1)
    $tasks = @()
    for ($index = 1; $index -le $collection.Count; $index++) {
        $tasks += $collection.Item($index)
    }
    if ($payload.command -eq 'list') {
        $items = @()
        foreach ($task in $tasks) {
            if ($task.Name.StartsWith('TradingViewMcpSupport__', [StringComparison]::Ordinal)) {
                $items += @{ taskName = [string]$task.Name; enabled = [bool]$task.Enabled }
            }
        }
        @{ ok = $true; items = $items } | ConvertTo-Json -Compress -Depth 5
    } elseif ($payload.command -eq 'remove') {
        $target = 'TradingViewMcpSupport__' + $payload.name
        $found = $false
        foreach ($task in $tasks) {
            if ([string]::Equals($task.Name, $target, [StringComparison]::OrdinalIgnoreCase)) {
                if (-not [string]::Equals($task.Name, $target, [StringComparison]::Ordinal)) {
                    @{ ok = $false; code = 'SCHEDULE_TASK_NAME_CONFLICT' } |
                        ConvertTo-Json -Compress
                    exit 0
                }
                $found = $true
                break
            }
        }
        if ($found) {
            try {
                $folder.DeleteTask($target, 0)
            } catch {
                # A concurrent delete is the only absence we classify by HRESULT.
                if ($_.Exception.HResult -eq -2147024894) {
                    $found = $false
                } else {
                    throw
                }
            }
        }
        @{ ok = $true; removed = $found } | ConvertTo-Json -Compress
    } elseif ($payload.command -eq 'apply') {
        $target = 'TradingViewMcpSupport__' + $payload.name
        $found = $false
        foreach ($task in $tasks) {
            if ([string]::Equals($task.Name, $target, [StringComparison]::OrdinalIgnoreCase)) {
                if (-not [string]::Equals($task.Name, $target, [StringComparison]::Ordinal)) {
                    @{ ok = $false; code = 'SCHEDULE_TASK_NAME_CONFLICT' } |
                        ConvertTo-Json -Compress
                    exit 0
                }
                $found = $true
                break
            }
        }
        $definition = $service.NewTask(0)
        $definition.RegistrationInfo.Description = 'TradingView MCP Support Job'
        $definition.Principal.UserId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        $definition.Principal.LogonType = 3
        $definition.Principal.RunLevel = 0
        $definition.Settings.Enabled = $true
        $definition.Settings.Hidden = $true
        $definition.Settings.MultipleInstances = 2
        $trigger = $definition.Triggers.Create(2)
        $trigger.DaysInterval = 1
        $trigger.StartBoundary = $payload.startBoundary
        $action = $definition.Actions.Create(0)
        $action.Path = $payload.powershell
        $action.Arguments = $payload.actionArguments
        $action.WorkingDirectory = $payload.projectRoot
        $null = $folder.RegisterTaskDefinition($target, $definition, 6, $null, $null, 3, $null)
        @{ ok = $true; result = $(if ($found) { 'updated' } else { 'created' }) } |
            ConvertTo-Json -Compress
    } else {
        @{ ok = $false; code = 'SCHEDULE_OPERATION_ERROR' } | ConvertTo-Json -Compress
    }
} catch {
    @{ ok = $false; code = 'SCHEDULE_OPERATION_ERROR' } | ConvertTo-Json -Compress
}
"""


def _task_name(name: str, project_root: Path) -> str:
    definition_path(project_root / "jobs", name, project_root=project_root)
    return f"{TASK_PREFIX}{name}"


def _safe_action_paths(project_root: Path) -> tuple[str, str]:
    root = str(project_root.resolve())
    app = str(project_root.resolve() / "app.bat")
    if _UNSAFE_ACTION_PATH.search(root) or _UNSAFE_ACTION_PATH.search(app):
        raise ConfigError("CONFIG_NAME_INVALID", "Repository path cannot be used in Task action")
    if not Path(app).is_file():
        raise ConfigError("CONFIG_FILE_NOT_FOUND", "Task launcher app.bat is missing")
    return root, app


def _powershell_path() -> str:
    system_root = os.environ.get("SystemRoot")
    if not system_root:
        raise AppError("SCHEDULE_UNSUPPORTED", "Windows PowerShell is unavailable")
    path = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not path.is_file():
        raise AppError("SCHEDULE_UNSUPPORTED", "Windows PowerShell is unavailable")
    return str(path)


def _action_arguments(root: str, app: str, name: str) -> str:
    data = json.dumps(
        {"projectRoot": root, "appBat": app, "name": name},
        ensure_ascii=True, separators=(",", ":"),
    )
    encoded_payload = base64.b64encode(data.encode("utf-8")).decode("ascii")
    source = _ACTION_SCRIPT.replace("{encoded_payload}", encoded_payload)
    encoded_source = base64.b64encode(source.encode("utf-16-le")).decode("ascii")
    return f"-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded_source}"


def _next_boundary(time: str, *, now: datetime | None = None) -> str:
    present = now or datetime.now(TOKYO)
    hour, minute = (int(part) for part in time.split(":"))
    candidate = present.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= present:
        candidate += timedelta(days=1)
    return candidate.isoformat(timespec="seconds")


def _bridge(request: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        raise AppError("SCHEDULE_UNSUPPORTED", "Windows Task Scheduler is unavailable")
    encoded = _COM_SCRIPT.encode("utf-16-le")
    command = [
        _powershell_path(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", base64.b64encode(encoded).decode("ascii"),
    ]
    try:
        result = subprocess.run(
            command,
            input=json.dumps(request, ensure_ascii=True, separators=(",", ":")),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_BRIDGE_TIMEOUT_SECONDS,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError("SCHEDULE_TIMEOUT", "Task Scheduler operation timed out") from exc
    except OSError as exc:
        raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler is unavailable") from exc
    if result.returncode != 0:
        raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler operation failed")
    try:
        response = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler response is invalid") from exc
    if isinstance(response, dict) and response.get("code") == "SCHEDULE_TASK_NAME_CONFLICT":
        raise AppError("SCHEDULE_TASK_NAME_CONFLICT", "Task name conflicts with an existing task")
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler operation failed")
    return response


def _envelope(operation: str, **fields: Any) -> dict[str, Any]:
    return {"schemaVersion": 1, "status": "success", "operation": operation, **fields, "errors": []}


def _validated_jobs(project_root: Path) -> tuple[JobDefinition, ...]:
    jobs: list[JobDefinition] = []
    for name in list_job_names(project_root):
        job = load_job_by_name(name, project_root)
        if job.task.type == "screening":
            validate_job_screening_reference(job, project_root)
        jobs.append(job)
    return tuple(jobs)


def apply_schedules(project_root: Path) -> dict[str, Any]:
    """Validate every Job before registering enabled daily tasks."""
    if platform.system() != "Windows":
        raise AppError("SCHEDULE_UNSUPPORTED", "Windows Task Scheduler is unavailable")
    jobs = _validated_jobs(project_root)
    for job in jobs:
        if job.enabled and job.task.type == "builtin":
            if job.task.definition not in BUILTINS:
                raise AppError("JOB_TASK_UNAVAILABLE", "Builtin Job cannot be scheduled")
            if job.output.watchlistSync:
                raise ConfigError(
                    "CONFIG_VALIDATION_ERROR", "Builtin Job cannot sync a Watchlist", "output.watchlistSync"
                )
        if job.enabled and job.schedule.timezone != "Asia/Tokyo":
            raise AppError(
                "SCHEDULE_TIMEZONE_UNSUPPORTED", "Job timezone is unsupported for scheduling"
            )
    root, app = _safe_action_paths(project_root)
    powershell = _powershell_path()
    payload = _envelope("schedule_apply", items=[])
    for job in jobs:
        task_name = _task_name(job.name, project_root)
        if not job.enabled:
            payload["items"].append({
                "jobName": job.name, "taskName": task_name, "result": "skipped",
                "reason": "disabled",
            })
            continue
        try:
            answer = _bridge({
                "command": "apply", "name": job.name, "projectRoot": root,
                "powershell": powershell,
                "actionArguments": _action_arguments(root, app, job.name),
                "startBoundary": _next_boundary(job.schedule.time),
            })
            result = answer.get("result")
            if result not in {"created", "updated"}:
                raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler response is invalid")
            payload["items"].append({
                "jobName": job.name, "taskName": task_name, "result": result,
            })
        except AppError as exc:
            payload["status"] = "failed"
            payload["items"].append({
                "jobName": job.name, "taskName": task_name, "result": "failed",
                "error": {"code": exc.code, "message": exc.message},
            })
            payload["errors"].append({"code": exc.code, "message": exc.message})
            break
    return payload


def list_schedules(project_root: Path) -> dict[str, Any]:
    answer = _bridge({"command": "list"})
    items = answer.get("items")
    if not isinstance(items, list):
        raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler response is invalid")
    tasks: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler response is invalid")
        name = item.get("taskName")
        enabled = item.get("enabled")
        if not isinstance(name, str) or type(enabled) is not bool:
            raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler response is invalid")
        if name.startswith(TASK_PREFIX):
            tasks.append({"taskName": name, "jobName": name[len(TASK_PREFIX):], "enabled": enabled})
    return _envelope("schedule_list", tasks=sorted(tasks, key=lambda item: item["taskName"]))


def remove_schedule(name: str, project_root: Path) -> dict[str, Any]:
    task_name = _task_name(name, project_root)
    answer = _bridge({"command": "remove", "name": name})
    removed = answer.get("removed")
    if type(removed) is not bool:
        raise AppError("SCHEDULE_OPERATION_ERROR", "Task Scheduler response is invalid")
    return _envelope("schedule_remove", taskName=task_name, jobName=name, removed=removed)
