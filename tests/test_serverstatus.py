from pydantic import HttpUrl, AnyHttpUrl, TypeAdapter

import pprint
import json
import pytest
from _pytest.fixtures import fixture
from unittest import mock
from rcon.server_status.serverstatus import (
    get_map_image,
    get_mapinfo_message,
    webhook_config,
    section_enum,
)

from rcon.user_config.serverstatus import (
    ServerStatusUserConfig,
    icons_config,
)

public_info_string = """{
    "result": {
        "current_map": {
            "just_name": "hurtgenforest",
            "human_name": "Hürtgen Forest",
            "name": "hurtgenforest_warfare_V2_night",
            "start": 1704478913
        },
        "next_map": {
            "just_name": "foy",
            "human_name": "Foy",
            "name": "foy_warfare",
            "start": null
        },
        "player_count": 64,
        "max_player_count": 100,
        "players": {
            "allied": 32,
            "axis": 32
        },
        "score": {
            "allied": 1,
            "axis": 4
        },
        "raw_time_remaining": "0:28:40",
        "vote_status": {
            "total_votes": 0,
            "winning_maps": []
        },
        "name": "Mikey'sMarauders (US East 1 NY) / discord.gg/nJ5d8juQhb",
        "short_name": "mikeys-hllrcon",
        "public_stats_port": "7010",
        "public_stats_port_https": "7011"
    },
    "command": "public_info",
    "arguments": null,
    "failed": false,
    "error": null,
    "forwards_results": null
}"""


def test_basic_config():
    config = ServerStatusUserConfig(
        base_api_url=TypeAdapter(AnyHttpUrl).validate_python("http://example.com"),
        base_scoreboard_url=TypeAdapter(AnyHttpUrl).validate_python(
            "http://scoreboard.example.com"
        ),
        admin_desc_text="admin",
        status_desc_text="status",
        webhooks=[],
    )

    assert config.stats_url == TypeAdapter(AnyHttpUrl).validate_python(
        "http://example.com/api/get_live_game_stats"
    )
    assert config.info_url == TypeAdapter(AnyHttpUrl).validate_python(
        "http://example.com/api/public_info"
    )
    assert config.past_games_url == TypeAdapter(AnyHttpUrl).validate_python(
        "http://scoreboard.example.com/#/gamescoreboard"
    )

    assert config.colors.embed == int("0x041E42", 16)

    assert config.icons.warfare == "🟩"


def test_webhooks_config():
    config = ServerStatusUserConfig(
        base_api_url=TypeAdapter(AnyHttpUrl).validate_python("http://example.com"),
        base_scoreboard_url=TypeAdapter(AnyHttpUrl).validate_python(
            "http://scoreboard.example.com"
        ),
        admin_desc_text="admin",
        status_desc_text="status",
        webhooks=[
            webhook_config(
                webhook_url="http://webhook.com/webhook_1",
                sections=[section_enum.status],
            ),
            webhook_config(
                webhook_url="http://webhook.com/webhook_2",
                sections=[section_enum.status_no_pic],
            ),
        ],
    )

    assert config.webhooks[0].webhook_url == "http://webhook.com/webhook_1"
    assert config.webhooks[0].sections == ["status"]
    assert config.webhooks[1].webhook_url == "http://webhook.com/webhook_2"
    assert config.webhooks[1].sections == ["status_no_pic"]


def test_get_map_image_day():
    config = ServerStatusUserConfig(
        base_api_url=TypeAdapter(AnyHttpUrl).validate_python("http://example.com"),
        base_scoreboard_url=TypeAdapter(AnyHttpUrl).validate_python(
            "http://scoreboard.example.com"
        ),
    )

    public_info = json.loads(public_info_string)["result"]
    public_info["current_map"]["name"] = "hurtgenforest_warfare_V2"

    assert public_info["current_map"]["name"] == "hurtgenforest_warfare_V2"
    assert public_info["next_map"]["name"] == "foy_warfare"

    assert (
        get_map_image(public_info, config)
        == "http://scoreboard.example.com/maps/hurtgen.webp"
    )

def test_get_map_image_night():
    config = ServerStatusUserConfig(
        base_api_url=TypeAdapter(AnyHttpUrl).validate_python("http://example.com"),
        base_scoreboard_url=TypeAdapter(AnyHttpUrl).validate_python(
            "http://scoreboard.example.com"
        ),
    )

    public_info = json.loads(public_info_string)["result"]
    public_info["current_map"]["name"] = "hurtgenforest_warfare_V2_night"

    assert public_info["current_map"]["name"] == "hurtgenforest_warfare_V2_night"
    assert public_info["next_map"]["name"] == "foy_warfare"

    assert (
        get_map_image(public_info, config)
        == "http://scoreboard.example.com/maps/hurtgen-night.webp"
    )

# mortain_warfare_overcast
def test_get_map_image_overcast():
    config = ServerStatusUserConfig(
        base_api_url=TypeAdapter(AnyHttpUrl).validate_python("http://example.com"),
        base_scoreboard_url=TypeAdapter(AnyHttpUrl).validate_python(
            "http://scoreboard.example.com"
        ),
    )

    public_info = json.loads(public_info_string)["result"]
    public_info["current_map"]["name"] = "mortain_warfare_overcast"

    assert public_info["current_map"]["name"] == "mortain_warfare_overcast"
    assert public_info["next_map"]["name"] == "foy_warfare"

    assert (
        get_map_image(public_info, config)
        == "http://scoreboard.example.com/maps/mortain-overcast.webp"
    )

# map_rotation_string = """{
#     "result": [
#         "DRL_S_1944_Day_P_Skirmish",
#         "DRL_S_1944_Night_P_Skirmish",
#         "DRL_S_1944_P_Skirmish",
#         "ELA_S_1942_Night_P_Skirmish",
#         "ELA_S_1942_P_Skirmish"
#     ],
#     "command": "get_map_rotation",
#     "arguments": {},
#     "failed": false,
#     "error": "",
#     "forward_results": null
# }
# """

map_rotation_string = """{
    "result": [
        "DRL_S_1944_P_Skirmish",
        "stmariedumont_warfare",
        "carentan_offensive_ger",
        "ELA_S_1942_P_Skirmish",
        "purpleheartlane_warfare_night",
        "elalamein_warfare_night",
        "mortain_offensiveUS_overcast",
        "SMDM_S_1944_Rain_P_Skirmish",
        "mortain_offensiveger_day",
        "mortain_warfare_overcast",
        "driel_offensive_us",
        "elalamein_offensive_CW"
    ],
    "command": "get_map_rotation",
    "arguments": {},
    "failed": false,
    "error": "",
    "forward_results": null
}
"""


def test_get_mapinfo_message():
    config = ServerStatusUserConfig(
        base_api_url=TypeAdapter(AnyHttpUrl).validate_python("http://example.com"),
        base_scoreboard_url=TypeAdapter(AnyHttpUrl).validate_python(
            "http://scoreboard.example.com"
        ),
        icons=icons_config(warfare="🟩", day="⬜", night="🔳", offensive="🟥"),
    )

    map_rotation = json.loads(map_rotation_string)["result"]
    message = get_mapinfo_message(map_rotation, config)

    print(message)

    assert (
        message
        == """```🟨🌄 Skm Dwn  Driel             
🟩⬜ War Day  St. Marie Du Mont 
🟥⬜ Off Day  Carentan (GER)    
🟨⬜ Skm Day  El Alamein        
🟩🔳 War Ngt  Purple Heart Lane 
🟩🌆 War Dsk  El Alamein        
🟥🌥️ Off Ovc  Mortain (US)      
🟨☔ Skm Rn   St. Marie Du Mont 
🟥⬜ Off Day  Mortain (GER)     
🟩🌥️ War Ovc  Mortain           
🟥⬜ Off Day  Driel (GB)        
🟥⬜ Off Day  El Alamein (GB)   ```
"""
    )
