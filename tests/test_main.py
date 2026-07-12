from datetime import datetime

from briefing.main import should_run


def test_scheduled_runs_are_allowed_during_the_morning(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    assert should_run(datetime(2026, 7, 12, 7, 0))
    assert should_run(datetime(2026, 7, 12, 11, 59))


def test_scheduled_runs_are_skipped_outside_the_delivery_window(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    assert not should_run(datetime(2026, 7, 12, 6, 59))
    assert not should_run(datetime(2026, 7, 12, 12, 0))


def test_manual_runs_are_not_time_limited(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    assert should_run(datetime(2026, 7, 12, 15, 0))

