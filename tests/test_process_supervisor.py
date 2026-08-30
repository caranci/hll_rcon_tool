import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

import textwrap
import time
from pathlib import Path
from xmlrpc.client import Fault, ServerProxy

import pytest

from rcon.process_supervisor.config import (
    ProgramConfig,
    SupervisorConfig,
    interpolate,
    load_config,
    parse_byte_size,
    parse_environment,
)
from rcon.process_supervisor.logging_setup import configure_logging
from rcon.process_supervisor.manager import ProcessSupervisor
from rcon.process_supervisor.rpc import start_rpc_server
from rcon.process_supervisor.states import ProcessState


def test_interpolate_env_variable():
    assert interpolate("foo_%(ENV_SERVER_NUMBER)s.log", {"SERVER_NUMBER": "3"}) == "foo_3.log"


def test_parse_environment():
    assert parse_environment("LOGGING_FILENAME=a.log,HLL_DB_DISABLE_CONNECTION_POOL=1") == {
        "LOGGING_FILENAME": "a.log",
        "HLL_DB_DISABLE_CONNECTION_POOL": "1",
    }


def test_load_config_parses_programs(tmp_path):
    config_text = textwrap.dedent(
        """
        [inet_http_server]
        port=127.0.0.1:9123

        [program:test_prog]
        command=/bin/sleep 30
        environment=LOGGING_FILENAME=test_%(ENV_SERVER_NUMBER)s.log
        autostart=false
        autorestart=unexpected
        startretries=2
        startsecs=0
        """
    )
    config_path = tmp_path / "supervisord.conf"
    config_path.write_text(config_text)

    config = load_config(config_path, {"SERVER_NUMBER": "7"})
    assert config.rpc_host == "127.0.0.1"
    assert config.rpc_port == 9123
    assert "test_prog" in config.programs
    prog = config.programs["test_prog"]
    assert prog.command == ["/bin/sleep", "30"]
    assert prog.environment["LOGGING_FILENAME"] == "test_7.log"
    assert prog.autostart is False
    assert prog.autorestart == "unexpected"
    assert prog.startretries == 2
    assert prog.startsecs == 0


def test_load_repo_supervisord_conf():
    config_path = Path(__file__).resolve().parents[1] / "config" / "supervisord.conf"
    env = {
        "SERVER_NUMBER": "1",
        "HLL_REDIS_URL": "redis://localhost:6379/0",
        "HLL_REDIS_HOST": "localhost",
        "HLL_REDIS_PORT": "6379",
        "HLL_REDIS_DB": "0",
    }
    config = load_config(config_path, env)
    expected = {
        "broadcasts",
        "expiring_vips",
        "seed_vip",
        "log_event_loop",
        "log_stream",
        "log_recorder",
        "auto_settings",
        "routines",
        "workers",
        "live_stats_refresh",
        "scoreboard",
        "server_status",
        "automod",
        "blacklists",
        "watch_killrate",
        "cron",
        "scheduler",
    }
    assert expected.issubset(set(config.programs))
    assert config.logfile == "/logs/supervisord.log"
    assert config.logfile_maxbytes == 50 * 1024 * 1024
    assert config.logfile_backups == 10


def test_parse_byte_size():
    assert parse_byte_size("50MB") == 50 * 1024 * 1024
    assert parse_byte_size("1024") == 1024


def test_load_config_parses_supervisord_logfile(tmp_path):
    config_text = textwrap.dedent(
        """
        [supervisord]
        logfile=%(ENV_LOG_DIR)s/supervisord.log
        logfile_maxbytes=10MB
        logfile_backups=3

        [program:demo]
        command=/bin/true
        autostart=false
        """
    )
    config_path = tmp_path / "supervisord.conf"
    config_path.write_text(config_text)
    config = load_config(config_path, {"LOG_DIR": str(tmp_path / "logs")})
    assert config.logfile == str(tmp_path / "logs" / "supervisord.log")
    assert config.logfile_maxbytes == 10 * 1024 * 1024
    assert config.logfile_backups == 3


def test_arbiter_logs_spawn_and_stop_to_logfile(tmp_path):
    logfile = tmp_path / "supervisord.log"
    config = SupervisorConfig(
        programs={
            "demo": ProgramConfig(
                name="demo",
                command=["/bin/sleep", "30"],
                environment={"LOGGING_FILENAME": "demo.log"},
                autostart=False,
                startsecs=0,
            )
        },
        logfile=str(logfile),
    )
    configure_logging(config)
    supervisor = ProcessSupervisor(config, base_environ={"LOGGING_PATH": str(tmp_path)})
    supervisor.start_process("demo")
    supervisor.stop_process("demo")

    contents = logfile.read_text()
    assert "Spawned 'demo'" in contents
    assert "entered RUNNING state" in contents
    assert "Stopped process 'demo' via RPC" in contents


def _make_supervisor(tmp_path: Path, command: list[str], **overrides) -> ProcessSupervisor:
    program = {
        "name": "demo",
        "command": command,
        "environment": {"LOGGING_FILENAME": "demo.log"},
        "autostart": False,
        "autorestart": "unexpected",
        "startretries": 2,
        "startsecs": 0,
        "stopsignal": "TERM",
        "stopwaitsecs": 2,
        "directory": None,
    }
    program.update(overrides)
    from rcon.process_supervisor.config import ProgramConfig

    config = SupervisorConfig(
        programs={
            "demo": ProgramConfig(**program),
        }
    )
    env = {"LOGGING_PATH": str(tmp_path)}
    return ProcessSupervisor(config, base_environ=env)


def test_start_stop_lifecycle(tmp_path):
    supervisor = _make_supervisor(tmp_path, ["/bin/sleep", "30"], startsecs=0)
    supervisor.start_process("demo")
    info = supervisor.get_process_info("demo")
    assert info["state"] == ProcessState.RUNNING
    assert info["statename"] == "RUNNING"
    assert info["pid"] > 0
    assert "uptime" in info["description"]

    supervisor.stop_process("demo")
    info = supervisor.get_process_info("demo")
    assert info["state"] == ProcessState.STOPPED
    assert info["pid"] == 0


def test_start_failure_becomes_fatal(tmp_path):
    supervisor = _make_supervisor(
        tmp_path,
        ["/bin/sh", "-c", "exit 1"],
        startretries=1,
        startsecs=1,
    )
    supervisor.start_process("demo")
    deadline = time.time() + 5
    while time.time() < deadline:
        supervisor.tick()
        if supervisor.get_process_info("demo")["state"] == ProcessState.FATAL:
            break
        time.sleep(0.05)
    assert supervisor.get_process_info("demo")["state"] == ProcessState.FATAL


def test_autorestart_unexpected_only_on_nonzero_exit(tmp_path):
    supervisor = _make_supervisor(
        tmp_path,
        ["/bin/sh", "-c", "exit 0"],
        autorestart="unexpected",
        startsecs=0,
    )
    supervisor.start_process("demo")
    supervisor.tick()
    time.sleep(0.1)
    supervisor.tick()
    assert supervisor.get_process_info("demo")["state"] == ProcessState.EXITED

    supervisor = _make_supervisor(
        tmp_path,
        ["/bin/sh", "-c", "exit 2"],
        autorestart="unexpected",
        startsecs=0,
    )
    supervisor.start_process("demo")
    deadline = time.time() + 3
    while time.time() < deadline:
        supervisor.tick()
        state = supervisor.get_process_info("demo")["state"]
        if state in {ProcessState.BACKOFF, ProcessState.STARTING, ProcessState.RUNNING}:
            break
        time.sleep(0.05)
    assert supervisor.get_process_info("demo")["state"] in {
        ProcessState.BACKOFF,
        ProcessState.STARTING,
        ProcessState.RUNNING,
    }


def test_rpc_start_stop_and_faults(tmp_path):
    supervisor = _make_supervisor(tmp_path, ["/bin/sleep", "30"], startsecs=0)
    server = start_rpc_server(supervisor, "127.0.0.1", 0)
    host, port = server.server_address
    client = ServerProxy(f"http://{host}:{port}/RPC2", allow_none=True)

    processes = client.supervisor.getAllProcessInfo()
    assert len(processes) == 1
    assert set(processes[0]) >= {
        "name",
        "group",
        "description",
        "start",
        "stop",
        "now",
        "state",
        "statename",
        "spawnerr",
        "exitstatus",
        "pid",
        "stdout_logfile",
    }

    assert client.supervisor.startProcess("demo") is True
    info = client.supervisor.getProcessInfo("demo")
    assert info["state"] == ProcessState.RUNNING

    with pytest.raises(Fault) as already_started:
        client.supervisor.startProcess("demo")
    assert already_started.value.faultCode == 60

    assert client.supervisor.stopProcess("demo") is True
    with pytest.raises(Fault) as not_running:
        client.supervisor.stopProcess("demo")
    assert not_running.value.faultCode == 70

    with pytest.raises(Fault) as bad_name:
        client.supervisor.startProcess("missing")
    assert bad_name.value.faultCode == 10

    server.shutdown()


def test_autostart_on_run(tmp_path):
    supervisor = _make_supervisor(
        tmp_path,
        ["/bin/sleep", "1"],
        autostart=True,
        startsecs=0,
    )

    def shutdown_soon():
        time.sleep(0.2)
        supervisor.request_shutdown()

    import threading

    threading.Thread(target=shutdown_soon, daemon=True).start()
    exit_code = supervisor.run()
    assert exit_code == 0
