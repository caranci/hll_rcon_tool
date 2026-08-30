import os
from contextlib import contextmanager
from unittest import mock

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon.process_supervisor.config import ProgramConfig
from rcon.process_supervisor.registry import (
    REGISTERED_PROGRAMS,
    _parse_log_recorder_args,
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
    monkeypatch.setattr("rcon.broadcast.run", called)
    run_program("broadcasts", [])
    called.assert_called_once_with()


def test_run_program_expiring_vips(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.expiring_vips.service.run", called)
    run_program("expiring_vips", [])
    called.assert_called_once_with()


def test_run_program_seed_vip_success(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.seed_vip.service.run", called)
    run_program("seed_vip", [])
    called.assert_called_once_with()


def test_run_program_seed_vip_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.seed_vip.service.run",
        mock.Mock(side_effect=RuntimeError("boom")),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("seed_vip", [])
    assert exc.value.code == 1


def test_run_program_log_event_loop(monkeypatch):
    hooks = mock.Mock()
    monkeypatch.setattr("rcon.process_supervisor.registry.ensure_log_loop_hooks", hooks)

    @contextmanager
    def fake_invalidates(*_args, **_kwargs):
        yield

    loop_instance = mock.Mock()
    loop_class = mock.Mock(return_value=loop_instance)
    monkeypatch.setattr("rcon.cache_utils.invalidates", fake_invalidates)
    monkeypatch.setattr("rcon.logs.loop.LogLoop", loop_class)

    run_program("log_event_loop", [])
    hooks.assert_called_once_with()
    loop_instance.run.assert_called_once_with()


def test_run_program_log_event_loop_failure_exits(monkeypatch):
    monkeypatch.setattr("rcon.process_supervisor.registry.ensure_log_loop_hooks", lambda: None)

    @contextmanager
    def fake_invalidates(*_args, **_kwargs):
        yield

    monkeypatch.setattr("rcon.cache_utils.invalidates", fake_invalidates)
    monkeypatch.setattr(
        "rcon.logs.loop.LogLoop",
        mock.Mock(return_value=mock.Mock(run=mock.Mock(side_effect=RuntimeError("fail")))),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("log_event_loop", [])
    assert exc.value.code == 1


def test_run_program_log_stream_enabled(monkeypatch):
    config = mock.Mock(enabled=True)
    stream = mock.Mock()
    monkeypatch.setattr(
        "rcon.user_config.log_stream.LogStreamUserConfig.load_from_db",
        mock.Mock(return_value=config),
    )
    monkeypatch.setattr("rcon.logs.stream.LogStream", mock.Mock(return_value=stream))
    run_program("log_stream", [])
    stream.clear.assert_called_once_with()
    stream.run.assert_called_once_with()


def test_run_program_log_stream_disabled(monkeypatch):
    config = mock.Mock(enabled=False)
    stream = mock.Mock()
    monkeypatch.setattr(
        "rcon.user_config.log_stream.LogStreamUserConfig.load_from_db",
        mock.Mock(return_value=config),
    )
    monkeypatch.setattr("rcon.logs.stream.LogStream", mock.Mock(return_value=stream))
    run_program("log_stream", [])
    stream.clear.assert_called_once_with()
    stream.run.assert_not_called()


def test_run_program_log_stream_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.user_config.log_stream.LogStreamUserConfig.load_from_db",
        mock.Mock(side_effect=RuntimeError("db")),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("log_stream", [])
    assert exc.value.code == 1


def test_run_program_log_recorder(monkeypatch):
    recorder = mock.Mock()
    recorder_class = mock.Mock(return_value=recorder)
    monkeypatch.setattr("rcon.logs.recorder.LogRecorder", recorder_class)
    run_program("log_recorder", ["-i", "20", "-n"])
    recorder_class.assert_called_once_with(20)
    recorder.run.assert_called_once_with(run_immediately=True)


def test_run_program_auto_settings_and_routines(monkeypatch):
    auto_settings = mock.Mock()
    routines = mock.Mock()
    monkeypatch.setattr("rcon.auto_settings.run", auto_settings)
    monkeypatch.setattr("rcon.routines.run", routines)
    run_program("auto_settings", [])
    run_program("routines", [])
    auto_settings.assert_called_once_with()
    routines.assert_called_once_with()


def test_run_program_live_stats_refresh(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.player_stats.live_stats_loop", called)
    run_program("live_stats_refresh", [])
    called.assert_called_once_with()


def test_run_program_live_stats_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(
        "rcon.player_stats.live_stats_loop",
        mock.Mock(side_effect=KeyboardInterrupt),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("live_stats_refresh", [])
    assert exc.value.code == 0


def test_run_program_live_stats_failure_exits(monkeypatch):
    monkeypatch.setattr(
        "rcon.player_stats.live_stats_loop",
        mock.Mock(side_effect=RuntimeError("stats")),
    )
    with pytest.raises(SystemExit) as exc:
        run_program("live_stats_refresh", [])
    assert exc.value.code == 1


def test_run_program_scoreboard_missing_volume_exits(monkeypatch):
    path_instance = mock.Mock()
    path_instance.exists.return_value = False
    monkeypatch.setattr("pathlib.Path", mock.Mock(return_value=path_instance))
    with pytest.raises(SystemExit) as exc:
        run_program("scoreboard", [])
    assert exc.value.code == -1


def test_run_program_scoreboard_success(monkeypatch):
    volume = mock.Mock()
    volume.exists.return_value = True
    db_path = mock.Mock()
    volume.__truediv__ = mock.Mock(return_value=db_path)

    def path_side_effect(arg: str):
        if arg == "/scoreboard_db":
            return volume
        return mock.Mock()

    monkeypatch.setattr("pathlib.Path", mock.Mock(side_effect=path_side_effect))
    engine = mock.Mock()
    monkeypatch.setattr("sqlalchemy.create_engine", mock.Mock(return_value=engine))
    create_all = mock.Mock()
    monkeypatch.setattr("rcon.scoreboard.Base.metadata.create_all", create_all)
    scoreboard_run = mock.Mock()
    monkeypatch.setattr("rcon.scoreboard.run", scoreboard_run)

    run_program("scoreboard", [])
    create_all.assert_called_once_with(engine)
    scoreboard_run.assert_called_once_with()


def test_run_program_scoreboard_failure_reraises(monkeypatch):
    volume = mock.Mock()
    volume.exists.return_value = True
    volume.__truediv__ = mock.Mock(return_value=mock.Mock())
    monkeypatch.setattr("pathlib.Path", mock.Mock(return_value=volume))
    monkeypatch.setattr("sqlalchemy.create_engine", mock.Mock(return_value=mock.Mock()))
    monkeypatch.setattr("rcon.scoreboard.Base.metadata.create_all", mock.Mock())
    monkeypatch.setattr("rcon.scoreboard.run", mock.Mock(side_effect=RuntimeError("scoreboard")))

    with pytest.raises(RuntimeError, match="scoreboard"):
        run_program("scoreboard", [])


def test_run_program_server_status_automod_blacklists(monkeypatch):
    serverstatus_run = mock.Mock()
    automod_run = mock.Mock()
    handler = mock.Mock()
    handler_class = mock.Mock(return_value=handler)
    monkeypatch.setattr("rcon.server_status.serverstatus.run", serverstatus_run)
    monkeypatch.setattr("rcon.automods.automod.run", automod_run)
    monkeypatch.setattr("rcon.blacklist.BlacklistCommandHandler", handler_class)

    run_program("server_status", [])
    run_program("automod", [])
    run_program("blacklists", [])

    serverstatus_run.assert_called_once_with()
    automod_run.assert_called_once_with()
    handler.run.assert_called_once_with()


def test_run_program_watch_killrate_success_and_failure(monkeypatch):
    called = mock.Mock()
    monkeypatch.setattr("rcon.watch_killrate.run", called)
    run_program("watch_killrate", [])
    called.assert_called_once_with()

    monkeypatch.setattr(
        "rcon.watch_killrate.run",
        mock.Mock(side_effect=RuntimeError("watch")),
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
        "server_status",
        "automod",
        "blacklists",
        "watch_killrate",
    }
    assert covered == REGISTERED_PROGRAMS
