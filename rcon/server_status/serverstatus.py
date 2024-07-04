import datetime
import logging
import os
import pathlib
import sqlite3
import time
from typing import Tuple, List, Dict, Callable
from sqlite3 import Connection
from urllib.parse import urljoin

from pydantic import ConfigDict

import requests
from requests.exceptions import ConnectionError, RequestException

import discord
import discord.utils
from discord.errors import HTTPException, NotFound

from rcon.cache_utils import ttl_cache
from rcon.commands import CommandFailedError, HLLServerError

from rcon.rcon import Rcon, get_rcon
from rcon import maps
from rcon.maps import UNKNOWN_MAP_NAME, parse_layer
from pprint import pprint

# from rcon.server_status.models import (
#     serverstatus_config,
#     section_enum,
#     webhook_config,
#     mapinfo_info,
# )

from rcon.user_config.serverstatus import (
    ServerStatusUserConfig,
    section_enum,
    webhook_config,
)

# when server closed connection unexpectedly?
from sqlalchemy.exc import OperationalError
from pydantic.dataclasses import dataclass


@dataclass
class mapinfo_info:
    name: str | None
    map: str | None
    next_map: str | None
    map_rotation: List[str] | None


class webhook_info(webhook_config):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    message_id: int
    webhook: discord.SyncWebhook


EMBEDS: Dict[section_enum, Callable]


# plans:
# config via config.yaml
# provide modular server info embeds
# allow multiple discord webhooks to allow for different classes of information
# remove reliance on public_info...
# don't want to keep changing / expose potentially private information!
# embeds for different informaion, including admin-only information

logger = logging.getLogger(__name__)


# @staticmethod
def get_our_config() -> ServerStatusUserConfig:
    config_key = "SERVERSTATUS"

    try:
        config = ServerStatusUserConfig.load_from_db()
    except Exception:
        logger.exception(f"Invalid {config_key} check your config/config.yml")
        raise
    server_number = int(os.getenv("SERVER_NUMBER", 0))
    logger.info(f"loaded config for server:{server_number}")
    logger.info(f"configs for {len(config.webhooks)} webhooks")
    return config


map_to_pict = {
    "carentan": "maps/carentan.webp",
    "carentan_night": "maps/carentan-night.webp",
    "driel": "maps/driel.webp",
    "driel_night": "maps/driel-night.webp",
    "elalamein": "maps/elalamein.webp",
    "elalamein_night": "maps/elalamein-night.webp",
    "foy": "maps/foy.webp",
    "foy_night": "maps/foy-night.webp",
    "hill400": "maps/hill400.webp",
    "hill400_night": "maps/hill400-night.webp",
    "hurtgenforest": "maps/hurtgen.webp",
    "hurtgenforest_night": "maps/hurtgen-night.webp",
    "kharkov": "maps/kharkov.webp",
    "kharkov_night": "maps/kharkov-night.webp",
    "kursk": "maps/kursk.webp",
    "kursk_night": "maps/kursk-night.webp",
    "mortain": "maps/mortain.webp",
    "mortain_night": "maps/mortain-night.webp",
    "mortain_dusk": "maps/mortain-dusk.webp",
    "mortain_overcast": "maps/mortain-overcast.webp",
    "omahabeach": "maps/omaha.webp",
    "omahabeach_night": "maps/omaha-night.webp",
    "purpleheartlane": "maps/phl.webp",
    "purpleheartlane_night": "maps/phl-night.webp",
    "stalingrad": "maps/stalingrad.webp",
    "stalingrad_night": "maps/stalingrad-night.webp",
    "stmariedumont": "maps/smdm.webp",
    "stmariedumont_night": "maps/smdm-night.webp",
    "stmereeglise": "maps/sme.webp",
    "stmereeglise_night": "maps/sme-night.webp",
    "utahbeach": "maps/utah.webp",
    "utahbeach_night": "maps/utah-night.webp",
    UNKNOWN_MAP_NAME: "maps/unknown.webp",
}


def get_map_image(server_info, config: ServerStatusUserConfig) -> str:
    map_name: str = server_info["current_map"]["name"]
    try:
        base_map_name, _ = map_name.lower().split("_", maxsplit=1)
    except ValueError:
        base_map_name = map_name

    if "night" in map_name.lower():
        base_map_name = base_map_name + "_night"
    elif "dusk" in map_name.lower():
        base_map_name = base_map_name + "_dusk"
    elif "overcast" in map_name.lower():
        base_map_name = base_map_name + "_overcast"

    img = map_to_pict.get(base_map_name, UNKNOWN_MAP_NAME)
    url = urljoin(str(config.scoreboard_url), img)
    return url


def get_public_info(config: ServerStatusUserConfig):
    try:
        public_info = requests.get(config.info_url).json()["result"]
    except requests.exceptions.JSONDecodeError:
        logger.error(
            f"Bad result from (invalid JSON) {config.info_url}, check your CRCON backend status"
        )
        raise
    except ConnectionError as e:
        logger.error(f"Error accessing {config.info_url}")
        raise
    return public_info


@ttl_cache(ttl=5)
def get_status_embed_no_pic(config: ServerStatusUserConfig) -> discord.Embed:
    public_info = get_public_info(config)

    # elapsed_time_minutes = (
    #     datetime.datetime.now()
    #     - datetime.datetime.fromtimestamp(public_info["current_map"]["start"])
    # ).total_seconds() / 60
    #
    # by observation, if public_info['raw_time_remaining'] == "0:00:00" then game
    # hasn't started... let's set elapsed time to 0!
    # but once the match starts the elapsed time is still wrong... :(
    # needs to be fixed in the current map start timestamp... in log scraping?
    # if public_info["raw_time_remaining"] == "0:00:00":
    #     elapsed_time_minutes = 0

    # simplify and remove links to stats... i really only want to see the status.
    # need to revert all this and just make my own module to make status embeds...
    embed = discord.Embed(
        title=f"{public_info['name']}",
        description=config.status_desc_text,
        color=config.colors.embed,
        timestamp=datetime.datetime.utcnow(),
    )

    # embed.add_field( name=f"Quick join link",    value=f"steam://connect/172.107.179.197:28115" , inline = False)
    embed.add_field(
        name=f"{config.current_map_text}",
        value=f"{public_info['current_map']['human_name']}",
    )

    embed.add_field(
        name="Score",
        value=f"Allies {public_info['score']['allied']} : Axis {public_info['score']['axis']}",
    )
    embed.add_field(
        name=f"{config.next_map_text}",
        value=f"{public_info['next_map']['human_name']}",
    )

    players_overall = f"{public_info['player_count']}/{public_info['max_player_count']}"
    players_team = f"Allies {public_info['players']['allied']} / Axis {public_info['players']['axis']}"
    # hack: fix bug where when 0 ppl in game one team will have a player. sigh.
    # hack: but how do we know when there really is only one player? argh!
    if public_info["player_count"] == 0:
        players_team = "Allies 0 / Axis 0"
    embed.add_field(
        name=f"Players",
        value=f"{players_overall} - {players_team}",
    )
    # embed.add_field(
    #     name=f"{ELAPSED_TIME}",
    #     value=f"{round(elapsed_time_minutes)} min. - {players_overall} {PLAYERS} ({players_team})",
    # )
    embed.add_field(
        name="Time remaining",
        value=f"{public_info['raw_time_remaining']}",
    )

    return embed


@ttl_cache(ttl=5)
def get_status_embed(config: ServerStatusUserConfig) -> discord.Embed:
    public_info = get_public_info(config)

    # get the no pic version...
    embed = get_status_embed_no_pic(config)

    # add the pic...
    embed.set_image(url=get_map_image(public_info, config))

    return embed


@ttl_cache(ttl=5)
def get_online_vips(rcon: Rcon) -> List[str]:
    online = []
    try:
        vips = rcon.get_vip_ids()
        players = rcon.get_players()
        vips_ids = set(a["steam_id_64"] for a in vips)

        for player in players:
            if player["steam_id_64"] in vips_ids:
                online.append(player["name"])

        online = sorted(map(str, online))
    except (CommandFailedError, HLLServerError, TimeoutError):
        # handle command failures by returning no vips...
        online = []
    return [discord.utils.escape_markdown(player) for player in online]


@ttl_cache(ttl=5)
def get_online_console_admins(rcon: Rcon) -> List[str]:
    online = []
    try:
        online = rcon.get_online_console_admins()
        online = sorted(map(str, online))
    except (CommandFailedError, HLLServerError, TimeoutError):
        # handle command failures by returning no admins...
        online = []
    return [discord.utils.escape_markdown(player) for player in online]


@ttl_cache(ttl=5)
def get_map_rotation() -> List[str]:
    rcon = get_rcon()
    map_rotation = []
    try:
        map_rotation = rcon.get_map_rotation()
    except (CommandFailedError, HLLServerError, TimeoutError):
        # handle command failures by returning no map rotation...
        map_rotation = []
    return map_rotation


@ttl_cache(ttl=5)
def get_admin_links_embed(config: ServerStatusUserConfig) -> discord.Embed:
    description = config.admin_desc_text
    embed = discord.Embed(
        title="Game config / stats for admins",
        description=description,
        color=config.colors.embed,
    )

    return embed


@ttl_cache(ttl=5)
def get_admin_vips_admins_embed(config: ServerStatusUserConfig) -> discord.Embed:
    rcon = get_rcon()

    embed = discord.Embed(
        color=config.colors.embed,
    )

    vips = get_online_vips(rcon)
    vips_str = ", ".join(vips)
    embed.add_field(
        inline=False,
        name="VIPs in game",
        value=f"{len(vips)}: {vips_str}",
    )

    admins = get_online_console_admins(rcon)
    admins_str = ", ".join(admins)
    embed.add_field(
        inline=False,
        name="Admins in game",
        value=f"{len(admins)}: {admins_str}",
    )

    return embed


@ttl_cache(ttl=5)
def get_admin_auto_settings_embed(config: ServerStatusUserConfig) -> discord.Embed:
    rcon = get_rcon()

    embed = discord.Embed(
        color=config.colors.embed,
    )
    embed.add_field(
        name="Max ping autokick",
        value=f"{rcon.get_max_ping_autokick()} msecs",
    )
    embed.add_field(
        name="Idle time autokick",
        value=f"{rcon.get_idle_autokick_time()} mins",
    )
    embed.add_field(
        name="Team switch cooldown",
        value=f"{rcon.get_team_switch_cooldown()} mins",
    )
    # embed.add_field(
    #     name="Autobalance threshold",
    #     value=f"{rcon.get_autobalance_threshold()}",
    # )

    return embed


def map_desc(map_layer: maps.Layer):
    # nb: keep desc constant length regardless of content for proper formatting
    # desc = "Warfare  "
    desc = "War"
    if map_layer.gamemode == maps.Gamemode.OFFENSIVE:
        # desc = f"Offensive ({get_map_side(map).upper()})"
        # desc = "Offensive"
        desc = "Off"
    elif map_layer.gamemode.is_small():
        desc = "Skm"

    if map_layer.environment == maps.Environment.DAWN:
        desc += " Dwn"
    elif map_layer.environment == maps.Environment.DAY:
        desc += " Day"
    elif map_layer.environment == maps.Environment.DUSK:
        desc += " Dsk"
    elif map_layer.environment == maps.Environment.NIGHT:
        desc += " Ngt"
    elif map_layer.environment == maps.Environment.OVERCAST:
        desc += " Ovc"
    elif map_layer.environment == maps.Environment.RAIN:
        desc += " Rn "

    return desc


def map_icons(map_layer: maps.Layer, config: ServerStatusUserConfig):
    type_icon = config.icons.warfare
    time_icon = config.icons.day
    if map_layer.environment == maps.Environment.DAWN:
        time_icon = config.icons.dawn
    elif map_layer.environment == maps.Environment.DAY:
        time_icon = config.icons.day
    elif map_layer.environment == maps.Environment.DUSK:
        time_icon = config.icons.dusk
    if map_layer.environment == maps.Environment.NIGHT:
        time_icon = config.icons.night
    elif map_layer.environment == maps.Environment.OVERCAST:
        time_icon = config.icons.overcast
    elif map_layer.environment == maps.Environment.RAIN:
        time_icon = config.icons.rain

    if map_layer.gamemode == maps.Gamemode.OFFENSIVE:
        type_icon = config.icons.offensive
    elif map_layer.gamemode.is_small():
        type_icon = config.icons.skirmish

    return f"{type_icon}{time_icon}"


def map_name_string(map_layer: maps.Layer):
    if map_layer.gamemode == maps.Gamemode.OFFENSIVE:
        if map_layer.attacking_faction:
            return f"{map_layer.map.prettyname} ({map_layer.attacking_faction.value.name.upper()})"
        else:
            return f"{map_layer.map.prettyname} (???)"

    return map_layer.map.prettyname


def get_mapinfo_message(map_rotation: List[str], config: ServerStatusUserConfig):
    parsed_map_rotation: list[maps.Layer] = [parse_layer(m) for m in map_rotation]
    map_message = ""
    if map_rotation:
        # max length of map name for formatting...
        max_str = max(parsed_map_rotation, key=lambda m: len(map_name_string(m)))
        max_len = len(map_name_string(max_str)) + 1
        map_table = "\n".join(
            [
                f"{map_icons(m, config)} {map_desc(m)}  {map_name_string(m):{max_len}}"
                for i, m in enumerate(parsed_map_rotation, start=1)
            ]
        )

        map_message += f"```{map_table}```\n"

    return map_message


@ttl_cache(ttl=5)
def get_map_info_embed(config: ServerStatusUserConfig) -> discord.Embed:
    map_rotation = get_map_rotation()

    embed = discord.Embed(
        title=f"Map Rotation",
        description=get_mapinfo_message(map_rotation, config),
        color=config.colors.embed,
        # timestamp=datetime.datetime.utcnow(),
    )
    return embed


def get_embeds(
    sections: List[section_enum], config: ServerStatusUserConfig
) -> List[discord.Embed]:
    embeds = []

    for section in sections:
        embeds.append(embed_callback[section](config))

    if len(embeds) > 0:
        # set timestamp on last embed only... avoids wasted whitespace...
        embeds[-1].timestamp = datetime.datetime.utcnow()

    print(embeds)
    return embeds


def get_embed_messageid_and_webhook(
    conn: Connection,
    server_number: int,
    webhook_url: str,
    config: ServerStatusUserConfig,
) -> Tuple[int, discord.SyncWebhook]:
    logger.info(f"get messageid and webhook for {webhook_url}")
    # get message_id from db for webhook url...
    message_id = conn.execute(
        "SELECT message_id FROM stats_messages WHERE server_number = ? AND message_type = ? AND webhook = ?",
        (server_number, "live", webhook_url),
    )
    message_id = message_id.fetchone()
    webhook = discord.SyncWebhook.from_url(webhook_url)

    # should put try block here to catch invalid json from endpoint...
    # happens when starting up?

    # check if embed is valid. if not create another...
    if message_id:
        (message_id,) = message_id
        logger.info("Resuming with message_id %s" % message_id)
    else:
        # todo: for now get just the status embed to setup a new message_id
        # in a discord channel. should make this get the correct embed. or
        # maybe just a skeleton placeholder embed?
        message = webhook.send(
            embeds=get_embeds([section_enum.status_no_pic], config),
            wait=True,
        )
        conn.execute(
            "INSERT INTO stats_messages VALUES (?, ?, ?, ?)",
            (server_number, "live", message.id, webhook_url),
        )
        conn.commit()
        message_id = message.id

    return message_id, webhook


def cleanup_orphaned_messages(
    conn: Connection, server_number: int, webhook_url: str
) -> None:
    conn.execute(
        "DELETE FROM stats_messages WHERE server_number = ? AND message_type = ? AND webhook = ?",
        (server_number, "live", webhook_url),
    )
    conn.commit()


# define section enum -> function lookup table...
embed_callback: Dict[section_enum, Callable] = {
    section_enum.status: get_status_embed,
    section_enum.status_no_pic: get_status_embed_no_pic,
    section_enum.admin_links: get_admin_links_embed,
    section_enum.admin_vips_admins: get_admin_vips_admins_embed,
    section_enum.admin_auto_settings: get_admin_auto_settings_embed,
    section_enum.map_info: get_map_info_embed,
}


def create_table(conn):
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats_messages (
                server_number INT,
                message_type VARCHAR(50),
                message_id VARCHAR(200),
                webhook VARCHAR(500)
            )
            """
        )
        conn.commit()
    except Exception as e:
        logger.exception(e)


def run():
    config: ServerStatusUserConfig = get_our_config()

    try:
        path = os.getenv("DISCORD_BOT_DATA_PATH", "/data")
        path = pathlib.Path(path) / pathlib.Path("server_status.db")
        logger.info(f"local db path: {str(path)}")
        logger.info(f"update interval: {config.update_interval} seconds")

        conn: Connection = sqlite3.connect(str(path))
        server_number = int(os.getenv("SERVER_NUMBER", 0))
        create_table(conn)

        # get embed info...
        # now have n webhooks to handle in config.webhooks
        # need to keep track of message ids, webhook_url, and embeds...
        # first try... iterate over all webhooks...
        wh_infos: List[webhook_info] = []
        for wh in config.webhooks:
            print(f"webhook_url: {wh.webhook_url}")
            print(f"webhook wections: {wh.sections}")

            message_id, webhook = get_embed_messageid_and_webhook(
                conn, server_number, wh.webhook_url, config
            )

            wh_info = webhook_info(
                webhook_url=wh.webhook_url,
                sections=wh.sections,
                webhook=webhook,
                message_id=message_id,
            )
            wh_infos.append(wh_info)

        # message_id, webhook = get_embed_messageid_and_webhook(
        #     conn, server_number, config.webhook_url
        # )
        # admin_message_id, admin_webhook = get_embed_messageid_and_webhook(
        #     conn, server_number, config.admin_webhook_url
        # )

        # event loop...
        while True:
            try:
                for wh in wh_infos:
                    wh.webhook.edit_message(
                        wh.message_id, embeds=get_embeds(wh.sections, config)
                    )

            except NotFound as ex:
                logger.exception(
                    "Message with ID in our records does not exist, cleaning up and restarting"
                )
                # todo: only cleanup messages that are actually orphaned, not all messages!
                for wh in wh_infos:
                    cleanup_orphaned_messages(conn, server_number, wh.webhook_url)

                raise ex
            except OperationalError as e:
                logger.exception("db operational error: ", e)
                raise
            except RuntimeError as e:
                # issue connection.py:_xor(msg).???
                logger.exception("game server command issue: ", e)
                time.sleep(5)
            except requests.exceptions.JSONDecodeError as e:
                logger.exception("Invalid JSON from backend", e)
                time.sleep(5)
            except (
                HTTPException,
                RequestException,
                ConnectionError,
                ConnectionResetError,
            ) as e:
                logger.exception("Temporary failure when trying to edit message", e)
                time.sleep(5)
            except Exception as e:
                logger.exception("Unable to edit message. Deleting record", e)
                # todo: only cleanup messages that are actually orphaned, not all messages!
                for wh in wh_infos:
                    cleanup_orphaned_messages(conn, server_number, wh.webhook_url)

                raise
            time.sleep(config.update_interval)
    except Exception as e:
        logger.exception("The bot stopped", e)
        raise


if __name__ == "__main__":
    run()
