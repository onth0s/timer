"""Tests for the `timer schedule` non-background scheduler."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from countdown.__main__ import main
from countdown.config import Config
from countdown.schedule import (
    STORE_FILENAME,
    ScheduleStore,
    format_remaining,
    wall_clock,
)
from tests.conftest import FakeClock, MockKeys

NOW = 1_700_000_000.0


@pytest.fixture
def sched(tmp_path, monkeypatch):
    """Isolated CWD/base + home stores and a frozen wall clock."""
    base = tmp_path / "base"
    home = tmp_path / "home" / ".config"
    base.mkdir()
    monkeypatch.setattr(ScheduleStore, "base_dir", base)
    monkeypatch.setattr(ScheduleStore, "home_config_dir", home)
    monkeypatch.setattr(Config, "path", tmp_path / "config.yaml")
    clock = FakeClock()
    clock.t = NOW
    monkeypatch.setattr("countdown.schedules_cli.time", clock.time)
    monkeypatch.setattr("countdown.schedules_cli.sleep", clock.sleep)
    return SimpleNamespace(
        base=base, home=home, clock=clock, runner=CliRunner()
    )


def run(sched, *args, **kwargs):
    """Invoke `timer schedule <args...>`."""
    return sched.runner.invoke(main, ["schedule", *args], **kwargs)


def patch_live_keys(sched, monkeypatch, at=2.0):
    """Exit the live view when the fake clock advances ``at`` seconds."""
    keys = MockKeys(sched.clock)
    keys.queue_at(sched.clock.t + at, "q")
    monkeypatch.setattr(
        "countdown.schedules_cli.check_for_keypress", keys.check
    )


# ---------------------------------------------------------------------------
# Adding
# ---------------------------------------------------------------------------


def test_add_relative_with_alias(sched):
    res = run(sched, "45m", "dishes")
    assert res.exit_code == 0, res.output
    store = ScheduleStore.load()
    assert len(store) == 1
    item = store.ordered()[0]
    assert item.spec == "45m"
    assert item.alias == "dishes"
    assert item.created == NOW
    assert item.due == NOW + 2700


def test_add_days(sched):
    res = run(sched, "2d1h30m", "bake")
    assert res.exit_code == 0, res.output
    item = ScheduleStore.load().ordered()[0]
    assert item.due == NOW + 178200


def test_add_unnamed(sched):
    res = run(sched, "5m")
    assert res.exit_code == 0, res.output
    item = ScheduleStore.load().ordered()[0]
    assert item.alias is None
    assert item.spec == "5m"


def test_add_target_clock_time(sched, monkeypatch):
    from datetime import datetime

    now_dt = datetime(2026, 8, 10, 15, 0, 0)

    class MockDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now_dt

    monkeypatch.setattr("countdown.timer.datetime", MockDateTime)
    res = run(sched, "-16:40", "standup")
    assert res.exit_code == 0, res.output
    item = ScheduleStore.load().ordered()[0]
    assert item.spec == "-16:40"
    assert item.due == NOW + 6000


def test_add_invalid_duration(sched):
    res = run(sched, "banana")
    assert res.exit_code != 0
    assert len(ScheduleStore.load()) == 0


@pytest.mark.parametrize(
    "alias",
    ["5m", "30", "list", "nuke", "at", "rm", "-foo", ""],
)
def test_alias_rejected(sched, alias):
    res = run(sched, "1h", alias)
    assert res.exit_code != 0, f"alias {alias!r} should be rejected"
    assert len(ScheduleStore.load()) == 0


def test_duplicate_alias_rejected(sched):
    assert run(sched, "1h", "x").exit_code == 0
    res = run(sched, "2h", "x")
    assert res.exit_code != 0
    assert len(ScheduleStore.load()) == 1


# ---------------------------------------------------------------------------
# Ordering & selection
# ---------------------------------------------------------------------------


def test_filo_newest_first(sched):
    run(sched, "1h", "aaa")
    run(sched, "2h", "bbb")
    store = ScheduleStore.load()
    assert [sc.alias for sc in store.ordered()] == ["bbb", "aaa"]


def test_list_newest_first(sched):
    run(sched, "1h", "aaa")
    run(sched, "2h", "bbb")
    out = run(sched, "list", "--now").output
    assert out.index("bbb") < out.index("aaa")


def test_checkin_by_number_and_alias_now(sched):
    run(sched, "1h", "aaa")
    run(sched, "2h", "bbb")
    res1 = run(sched, "1", "--now")
    assert res1.exit_code == 0, res1.output
    assert "2h" in res1.output
    res2 = run(sched, "2", "--now")
    assert "1h" in res2.output
    res3 = run(sched, "bbb", "--now")
    assert "2h" in res3.output


def test_checkin_out_of_range(sched):
    run(sched, "5m")
    res = run(sched, "7")
    assert res.exit_code != 0
    assert "1..1" in res.output


def test_now_skips_animation(sched, monkeypatch):
    captured = []

    def fake_run_countdown(total_seconds, **kwargs):
        captured.append(total_seconds)

    monkeypatch.setattr("countdown.__main__.run_countdown", fake_run_countdown)
    run(sched, "1h", "x")
    res = run(sched, "1", "--now")
    assert res.exit_code == 0, res.output
    assert captured == []


def test_animated_checkin_uses_remaining(sched, monkeypatch):
    captured = {}

    def fake_run_countdown(total_seconds, **kwargs):
        captured["total"] = total_seconds
        captured["show_hours"] = kwargs.get("show_hours")

    monkeypatch.setattr("countdown.__main__.run_countdown", fake_run_countdown)
    run(sched, "2h", "long")
    assert run(sched, "1").exit_code == 0
    assert captured["total"] == 7200
    assert captured["show_hours"] is True

    run(sched, "30m", "short")
    assert run(sched, "short").exit_code == 0
    assert captured["total"] == 1800
    assert captured["show_hours"] is False


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


def test_timeout_mark_in_list(sched):
    run(sched, "5m", "short")
    sched.clock.t += 400
    out = run(sched, "list", "--now").output
    assert "Timeout!" in out


def test_expired_checkin_launches_big_timer(sched, monkeypatch):
    captured = []

    def fake_run_countdown(total_seconds, **kwargs):
        captured.append((total_seconds, kwargs.get("show_hours")))

    monkeypatch.setattr("countdown.__main__.run_countdown", fake_run_countdown)
    run(sched, "5m", "short")
    sched.clock.t += 400
    res = run(sched, "short")
    assert res.exit_code == 0, res.output
    assert captured == [(0, False)]
    assert "00:00" in res.output or "Timed out" in res.output


def test_expired_checkin_now_shows_timeout_panel(sched, monkeypatch):
    captured = []

    def fake_run_countdown(total_seconds, **kwargs):
        captured.append(total_seconds)

    monkeypatch.setattr("countdown.__main__.run_countdown", fake_run_countdown)
    run(sched, "5m", "short")
    sched.clock.t += 400
    res = run(sched, "short", "--now")
    assert res.exit_code == 0, res.output
    assert "Timeout!" in res.output
    assert captured == []


# ---------------------------------------------------------------------------
# nuke
# ---------------------------------------------------------------------------


def test_nuke_confirm_abort(sched):
    run(sched, "1h", "x")
    run(sched, "2h", "y")
    res = run(sched, "nuke", input="n\n")
    assert res.exit_code != 0
    assert len(ScheduleStore.load()) == 2


def test_nuke_confirm_clears(sched):
    run(sched, "1h", "x")
    run(sched, "2h", "y")
    res = run(sched, "nuke", input="y\n")
    assert res.exit_code == 0, res.output
    assert len(ScheduleStore.load()) == 0


def test_nuke_empty_is_noop(sched):
    res = run(sched, "nuke", input="y\n")
    assert res.exit_code == 0, res.output


# ---------------------------------------------------------------------------
# expand / -e
# ---------------------------------------------------------------------------


def test_expand_checkin_launches_big_timer(sched, monkeypatch):
    captured = []

    def fake_run_countdown(total_seconds, **kwargs):
        captured.append(total_seconds)

    monkeypatch.setattr("countdown.__main__.run_countdown", fake_run_countdown)
    run(sched, "1h", "x")
    assert run(sched, "1", "--expand").exit_code == 0
    assert run(sched, "x", "-e").exit_code == 0
    assert captured == [3600, 3600]


def test_expand_add_then_launch(sched, monkeypatch):
    captured = {}

    def fake_run_countdown(total_seconds, **kwargs):
        captured["total"] = total_seconds

    monkeypatch.setattr("countdown.__main__.run_countdown", fake_run_countdown)
    run(sched, "1h", "x")
    res = run(sched, "30m", "y", "--expand")
    assert res.exit_code == 0, res.output
    store = ScheduleStore.load()
    assert len(store) == 2
    assert store.ordered()[0].alias == "y"
    assert captured["total"] == 1800


def test_now_expand_conflict(sched):
    run(sched, "1h", "x")
    res = run(sched, "1", "--now", "--expand")
    assert res.exit_code != 0
    assert "mutually exclusive" in res.output


# ---------------------------------------------------------------------------
# rm
# ---------------------------------------------------------------------------


def test_rm_by_alias(sched):
    run(sched, "1h", "x")
    run(sched, "2h", "y")
    res = run(sched, "rm", "x")
    assert res.exit_code == 0, res.output
    store = ScheduleStore.load()
    assert len(store) == 1
    assert store.ordered()[0].alias == "y"


def test_rm_by_number(sched):
    run(sched, "1h", "x")
    run(sched, "2h", "y")
    assert run(sched, "rm", "1").exit_code == 0
    store = ScheduleStore.load()
    assert len(store) == 1
    assert store.ordered()[0].alias == "x"


def test_rm_not_found(sched):
    run(sched, "1h", "x")
    res = run(sched, "rm", "ghost")
    assert res.exit_code != 0
    assert "ghost" in res.output
    res2 = run(sched, "rm", "9")
    assert res2.exit_code != 0
    assert "1..1" in res2.output
    assert len(ScheduleStore.load()) == 1


def test_rm_empty_store(sched):
    res = run(sched, "rm", "1")
    assert res.exit_code != 0
    assert "No schedules" in res.output


# ---------------------------------------------------------------------------
# list behavior & messages
# ---------------------------------------------------------------------------


def test_list_now_accepted(sched):
    run(sched, "1h", "x")
    res = run(sched, "list", "--now")
    assert res.exit_code == 0, res.output
    assert "x" in res.output


def test_list_unnamed_has_no_fake_alias(sched):
    run(sched, "90m")
    run(sched, "90m", "named")
    out = run(sched, "list", "--now").output
    assert "named" in out
    assert "90m" not in out
    assert "null" in out


def test_add_feedback_shows_path_and_number(sched):
    res = run(sched, "1h", "x")
    assert res.exit_code == 0, res.output
    assert "Scheduled" in res.output
    assert ":: due" in res.output
    assert "stack #1" in res.output
    assert "saved to" in res.output
    flat = res.output.replace("\n", "")
    assert str(sched.home / STORE_FILENAME) in flat


def test_unknown_token_message(sched):
    res = run(sched, "wibble")
    assert res.exit_code != 0
    assert "Unknown schedule or duration" in res.output


def test_load_rejects_duplicate_alias(sched):
    _dump(
        sched.base / STORE_FILENAME,
        [
            {"due": 1.0, "created": 0.5, "spec": "5m", "alias": "x"},
            {"due": 2.0, "created": 1.0, "spec": "5m", "alias": "x"},
        ],
    )
    with pytest.raises(ValueError, match="Duplicate alias"):
        ScheduleStore.load()


# ---------------------------------------------------------------------------
# Live ticking view
# ---------------------------------------------------------------------------


def test_bare_schedule_ticks_live(sched, monkeypatch):
    run(sched, "5m", "x")
    patch_live_keys(sched, monkeypatch, at=2.0)
    res = run(sched)
    assert res.exit_code == 0, res.output
    assert "4m58s" in res.output
    assert "Stopped schedule live view" in res.output
    assert "(watched 2s, 0 timed out)." in res.output


def test_list_defaults_to_live(sched, monkeypatch):
    run(sched, "5m", "x")
    patch_live_keys(sched, monkeypatch, at=0.0)
    res = run(sched, "list")
    assert res.exit_code == 0, res.output
    assert "Stopped schedule live view" in res.output


def test_list_now_is_static_snapshot(sched):
    run(sched, "5m", "x")
    res = run(sched, "list", "--now")
    assert res.exit_code == 0, res.output
    assert "Stopped schedule live view" not in res.output


def test_live_timeout_transition(sched, monkeypatch):
    run(sched, "5m", "x")
    patch_live_keys(sched, monkeypatch, at=0.0)
    sched.clock.t += 300
    res = run(sched, "list")
    assert res.exit_code == 0, res.output
    assert "Timeout!" in res.output
    assert "(watched 0s, 1 timed out)." in res.output


def test_live_empty_store_is_static(sched):
    res = run(sched)
    assert res.exit_code == 0, res.output
    assert "No schedules yet" in res.output
    assert "Stopped schedule live view" not in res.output


def test_live_keyboard_interrupt(sched, monkeypatch):
    run(sched, "5m", "x")
    sched.clock.raise_at(NOW + 2.0, KeyboardInterrupt())
    res = run(sched, "list")
    assert res.exit_code == 0, res.output
    assert "Stopped schedule live view" in res.output
    assert "(watched 2s, 0 timed out)." in res.output


def test_bare_now_static(sched):
    run(sched, "5m", "x")
    res = run(sched, "--now")
    assert res.exit_code == 0, res.output
    assert "Stopped schedule live view" not in res.output


def test_bare_expand_nothing(sched):
    run(sched, "5m", "x")
    res = run(sched, "--expand")
    assert res.exit_code != 0
    assert "Nothing to expand" in res.output


# ---------------------------------------------------------------------------
# Path precedence (CWD wins, else ~/.config)
# ---------------------------------------------------------------------------


def _dump(path: Path, schedules):
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schedules": schedules}), encoding="utf-8")


def test_resolve_falls_back_to_home(sched):
    assert ScheduleStore.resolve_path() == sched.home / STORE_FILENAME


def test_resolve_local_wins_when_present(sched):
    _dump(
        sched.base / STORE_FILENAME,
        [{"due": 1.0, "created": 0.5, "spec": "5m"}],
    )
    assert ScheduleStore.resolve_path() == sched.base / STORE_FILENAME


def test_store_round_trip_local(sched):
    _dump(sched.base / STORE_FILENAME, [])
    store = ScheduleStore.load()
    store.add(due=NOW + 120, created=NOW, spec="2m", alias="t")
    store.save()
    data = sched.base.joinpath(STORE_FILENAME).read_text(encoding="utf-8")
    assert "alias: t" in data
    assert not sched.home.joinpath(STORE_FILENAME).exists()


def test_store_switches_source_when_local_appears(sched):
    _dump(
        sched.home / STORE_FILENAME,
        [{"due": 9.0, "created": 8.0, "spec": "9s"}],
    )
    assert ScheduleStore.load().ordered()[0].due == 9.0
    _dump(
        sched.base / STORE_FILENAME,
        [{"due": 5.0, "created": 4.0, "spec": "5s"}],
    )
    assert ScheduleStore.load().ordered()[0].due == 5.0


def test_store_save_creates_home(sched):
    store = ScheduleStore.load()
    store.add(due=NOW + 60, created=NOW, spec="1m")
    store.save()
    assert (sched.home / STORE_FILENAME).exists()


def test_store_load_rejects_malformed(sched):
    sched.base.joinpath(STORE_FILENAME).write_text(
        "- just a list\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        ScheduleStore.load()
    sched.base.joinpath(STORE_FILENAME).write_text(
        "schedules:\n- due: nope\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        ScheduleStore.load()


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_format_remaining():
    assert format_remaining(93) == "1m33s"
    assert format_remaining(0) == "0s"
    assert format_remaining(-65) == "-1m5s"
    assert format_remaining(176400) == "2d1h"


def test_wall_clock_shape():
    text = wall_clock(1_700_000_000.0)
    assert len(text) == len("Mon 00:00")
    assert ":" in text
