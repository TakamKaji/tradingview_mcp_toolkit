"""Public read-only Screening and Job sample contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradingview_screening.jobs.loader import load_job_by_name, validate_job_screening_reference


@pytest.mark.parametrize("name", [
    "public_japan_value",
    "public_sp500",
    "public_oversold_healthy",
    "public_sp500_symbolset",
])
def test_public_screening_sample_jobs_are_read_only_and_manual(name: str) -> None:
    root = Path(__file__).resolve().parents[1]
    job = load_job_by_name(f"{name}_daily", root)
    screening = validate_job_screening_reference(job, root)

    assert job.name == f"{name}_daily"
    assert job.enabled is False
    assert job.task.type == "screening"
    assert job.task.definition == name
    assert job.output.save is True
    assert job.output.watchlistSync is False
    assert screening is not None
    assert screening.name == name
    assert screening.limit == 5
    assert screening.watchlist is not None
    assert screening.watchlist.enabled is False
