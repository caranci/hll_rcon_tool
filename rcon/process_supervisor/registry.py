"""Program name registry and lazy run() dispatch for worker children."""

from __future__ import annotations

import sys

from rcon.process_supervisor.config import ProgramConfig
from rcon.process_supervisor.programs import (
    LOG_LOOP_HOOK_MODULES,
    _parse_log_recorder_args,
    ensure_log_loop_hooks,
)

_PROGRAM_RUNNERS: dict[str, str] = {
    "broadcasts": "run_broadcasts",
    "expiring_vips": "run_expiring_vips",
    "seed_vip": "run_seed_vip",
    "log_event_loop": "run_log_event_loop",
    "log_stream": "run_log_stream",
    "log_recorder": "run_log_recorder",
    "auto_settings": "run_auto_settings",
    "routines": "run_routines",
    "live_stats_refresh": "run_live_stats_refresh",
    "scoreboard": "run_scoreboard",
    "automod": "run_automod",
    "blacklists": "run_blacklists",
    "watch_killrate": "run_watch_killrate",
}

REGISTERED_PROGRAMS = frozenset(_PROGRAM_RUNNERS)


def command_extra(program: ProgramConfig) -> list[str] | None:
    """Return extra argv for the worker, or None to spawn the INI command as-is."""

    if program.name not in REGISTERED_PROGRAMS:
        return None

    cmd = program.command
    if not cmd:
        return []

    if cmd[0].endswith("manage.py"):
        return cmd[2:]

    if len(cmd) >= 3 and cmd[1] == "-m":
        return []

    return cmd[1:]


def worker_argv(program: ProgramConfig) -> list[str]:
    extra = command_extra(program)
    if extra is None:
        return program.command
    return [
        sys.executable,
        "-m",
        "rcon.process_supervisor.worker",
        program.name,
        "--",
        *extra,
    ]


def run_program(name: str, extra: list[str]) -> None:
    attr = _PROGRAM_RUNNERS.get(name)
    if attr is None:
        raise KeyError(name)
    from rcon.process_supervisor import programs

    fn = getattr(programs, attr)
    if name == "log_recorder":
        fn(extra)
    else:
        fn()
