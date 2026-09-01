import os
from unittest import mock

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon.process_supervisor.config import ProgramConfig
from rcon.process_supervisor.registry import (
    _parse_log_recorder_args,
    adapter_names,
    command_extra,
    run_program,
)


def test_command_extra_empty_command_and_fallback():
    registered = ProgramConfig(name="broadcasts", command=[])
    assert command_extra(registered) == []

    fallback = ProgramConfig(name="broadcasts", command=["/usr/bin/custom", "arg"])
    assert command_extra(fallback) == ["arg"]

    unknown = ProgramConfig(name="workers", command=["rq", "worker"])
    assert command_extra(unknown) is None


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ([], (10, False)),
        (["-i", "5"], (5, False)),
        (["--interval", "15"], (15, False)),
        (["-t", "2"], (120, False)),
        (["--frequency-min", "3"], (180, False)),
        (["-n"], (10, True)),
        (["--now"], (10, True)),
        (["-i", "7", "-n"], (7, True)),
        (["unknown"], (10, False)),
    ],
)
def test_parse_log_recorder_args(extra, expected):
    assert _parse_log_recorder_args(extra) == expected


def test_run_program_broadcasts(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_broadcasts", called)
    run_program("broadcasts", [])
    called.assert_called_once_with()


def test_run_program_expiring_vips(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_expiring_vips", called)
    run_program("expiring_vips", [])
    called.assert_called_once_with()


def test_run_program_seed_vip_success(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_seed_vip", called)
    run_program("seed_vip", [])
    called.assert_called_once_with()


def test_run_program_seed_vip_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_seed_vip",
        mock.Mock(side_effect=SystemExit(1)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("seed_vip", [])
    assert exc.value.code == 1


def test_run_program_log_event_loop(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_log_event_loop", called)
    run_program("log_event_loop", [])
    called.assert_called_once_with()


def test_run_program_log_event_loop_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_log_event_loop",
        mock.Mock(side_effect=SystemExit(1)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("log_event_loop", [])
    assert exc.value.code == 1


def test_run_program_log_stream_success(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_log_stream", called)
    run_program("log_stream", [])
    called.assert_called_once_with()


def test_run_program_log_stream_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_log_stream",
        mock.Mock(side_effect=SystemExit(1)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("log_stream", [])
    assert exc.value.code == 1


def test_run_program_log_recorder(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_log_recorder", called)
    run_program("log_recorder", ["-i", "20", "-n"])
    called.assert_called_once_with(["-i", "20", "-n"])


def test_run_program_auto_settings_and_routines(monkeypatch):
    auto_settings = mock.Mock()
    routines = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_auto_settings", auto_settings)
    monkeypatch.setattr("rcon.process_supervisor.programs.run_routines", routines)
    run_program("auto_settings", [])
    run_program("routines", [])
    auto_settings.assert_called_once_with()
    routines.assert_called_once_with()


def test_run_program_live_stats_refresh(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_live_stats_refresh", called)
    run_program("live_stats_refresh", [])
    called.assert_called_once_with()


def test_run_program_live_stats_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_live_stats_refresh",
        mock.Mock(side_effect=SystemExit(0)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("live_stats_refresh", [])
    assert exc.value.code == 0


def test_run_program_live_stats_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_live_stats_refresh",
        mock.Mock(side_effect=SystemExit(1)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("live_stats_refresh", [])
    assert exc.value.code == 1


def test_run_program_scoreboard_success(monkeypatch):
    scoreboard_run = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_scoreboard", scoreboard_run)
    run_program("scoreboard", [])
    scoreboard_run.assert_called_once_with()


def test_run_program_scoreboard_missing_volume_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_scoreboard",
        mock.Mock(side_effect=SystemExit(-1)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("scoreboard", [])
    assert exc.value.code == -1


def test_run_program_scoreboard_failure_reraises(monkeypatch):
    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_scoreboard",
        mock.Mock(side_effect=RuntimeError("scoreboard")),
    )
    with pytest.raises(RuntimeError, match="scoreboard"):
        run_program("scoreboard", [])


def test_run_program_automod_blacklists(monkeypatch):
    automod_run = mock.Mock()
    blacklists_run = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_automod", automod_run)
    monkeypatch.setattr("rcon.process_supervisor.programs.run_blacklists", blacklists_run)

    run_program("automod", [])
    run_program("blacklists", [])

    automod_run.assert_called_once_with()
    blacklists_run.assert_called_once_with()


def test_run_program_watch_killrate_success_and_failure(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.programs.run_watch_killrate", called)
    run_program("watch_killrate", [])
    called.assert_called_once_with()

    monkeypatch.setattr(
        "rcon.process_supervisor.programs.run_watch_killrate",
        mock.Mock(side_effect=SystemExit(1)),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("watch_killrate", [])
    assert exc.value.code == 1


def test_all_registered_programs_have_dispatch_tests():
    covered = {
        "broadcasts",
        "expiring_vips",
        "seed_vip",
        "log_event_loop",
        "log_stream",
        "log_recorder",
        "auto_settings",
        "routines",
        "live_stats_refresh",
        "scoreboard",
        "automod",
        "blacklists",
        "watch_killrate",
    }
    assert covered == adapter_names()
