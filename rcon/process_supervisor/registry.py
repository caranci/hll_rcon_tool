"""Program name registry and lazy run() dispatch for worker children."""

from __future__ import annotations

import importlib
import logging
import sys

from rcon.process_supervisor.config import ProgramConfig

logger = logging.getLogger(__name__)

REGISTERED_PROGRAMS: frozenset[str] = frozenset(
    {
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
)

LOG_LOOP_HOOK_MODULES: tuple[str, ...] = (
    "rcon.hooks",
    "rcon.auto_kick",
    "rcon.automods.tk_autoban",
    "rcon.discord_chat",
    "rcon.recent_actions",
    "rcon.watchlist",
    "rcon.automods.automod",
)


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


def ensure_log_loop_hooks() -> None:
    for module_name in LOG_LOOP_HOOK_MODULES:
        importlib.import_module(module_name)


def _parse_log_recorder_args(extra: list[str]) -> tuple[int, bool]:
    interval = 10
    run_immediately = False
    index = 0
    while index < len(extra):
        token = extra[index]
        if token in ("-i", "--interval") and index + 1 < len(extra):
            interval = int(extra[index + 1])
            index += 2
            continue
        if token in ("-t", "--frequency-min") and index + 1 < len(extra):
            interval = int(extra[index + 1]) * 60
            index += 2
            continue
        if token in ("-n", "--now"):
            run_immediately = True
            index += 1
            continue
        index += 1

    return interval, run_immediately


def run_program(name: str, extra: list[str]) -> None:
    if name not in REGISTERED_PROGRAMS:
        raise KeyError(name)

    if name == "broadcasts":
        from rcon import broadcast

        broadcast.run()
        return

    if name == "expiring_vips":
        import rcon.expiring_vips.service

        rcon.expiring_vips.service.run()
        return

    if name == "seed_vip":
        import rcon.seed_vip.service

        try:
            rcon.seed_vip.service.run()
        except Exception:
            logger.exception("seed VIP stopped")
            sys.exit(1)
        return

    if name == "log_event_loop":
        from rcon.cache_utils import invalidates
        from rcon.discord_chat import get_handler
        from rcon.logs.loop import LogLoop, load_generic_hooks

        ensure_log_loop_hooks()
        with invalidates(load_generic_hooks, get_handler):
            try:
                LogLoop().run()
            except Exception:
                logger.exception("Chat recorder stopped")
                sys.exit(1)
        return

    if name == "log_stream":
        from rcon.logs.stream import LogStream
        from rcon.user_config.log_stream import LogStreamUserConfig

        try:
            config = LogStreamUserConfig.load_from_db()
            stream = LogStream()
            stream.clear()
            if config.enabled:
                stream.run()
        except Exception:
            logger.exception("Log stream stopped")
            sys.exit(1)
        return

    if name == "log_recorder":
        from rcon.logs.recorder import LogRecorder

        interval, run_immediately = _parse_log_recorder_args(extra)
        LogRecorder(interval).run(run_immediately=run_immediately)
        return

    if name == "auto_settings":
        from rcon import auto_settings

        auto_settings.run()
        return

    if name == "routines":
        from rcon import routines

        routines.run()
        return

    if name == "live_stats_refresh":
        from rcon.player_stats import live_stats_loop

        try:
            live_stats_loop()
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception:
            logger.exception("Stats loop stopped")
            sys.exit(1)
        return

    if name == "scoreboard":
        import pathlib as scoreboard_pathlib

        from sqlalchemy import create_engine

        from rcon.scoreboard import Base, run as scoreboard_run

        volume_path = scoreboard_pathlib.Path("/scoreboard_db")
        if not volume_path.exists():
            logger.fatal(
                "Your scoreboard volume is not configured correctly in your compose.yaml file."
            )
            sys.exit(-1)

        db_path = scoreboard_pathlib.Path("/scoreboard_db") / scoreboard_pathlib.Path(
            "./scoreboard.db"
        )
        engine = create_engine(
            f"sqlite:///file:{db_path}?mode=rwc&uri=true", echo=False
        )
        try:
            logger.info("Attempting to start scoreboard")
            Base.metadata.create_all(engine)
            scoreboard_run()
        except Exception:
            logger.exception("scoreboard failed unexpectedly")
            raise
        return

    if name == "automod":
        from rcon.automods import automod

        automod.run()
        return

    if name == "blacklists":
        from rcon.blacklist import BlacklistCommandHandler

        BlacklistCommandHandler().run()
        return

    if name == "watch_killrate":
        import rcon.watch_killrate

        try:
            rcon.watch_killrate.run()
        except Exception:
            logger.exception("Watch_KillRate stopped")
            sys.exit(1)
        return

    raise KeyError(name)
