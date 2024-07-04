from enum import Enum
from typing import Optional, TypedDict, List

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
    AnyHttpUrl,
    TypeAdapter,
)

from rcon.user_config.utils import BaseUserConfig, key_check, set_user_config
from rcon.utils import get_server_number

STATS_ENDPOINT = "/api/get_live_game_stats"
INFO_ENDPOINT = "/api/public_info"
API_ENDPOINT = "/api/"
PAST_GAMES_ENDPOINT = "/#/gamescoreboard"


ALL_STATS = "All stats on: "
AUTHOR_NAME = "STATS LIVE HLL FRANCE - click here"
# TODO: host this locally
AUTHOR_ICON_URL = "https://static.wixstatic.com/media/da3421_111b24ae66f64f73aa94efeb80b08f58~mv2.png/v1/fit/w_2500,h_1330,al_c/da3421_111b24ae66f64f73aa94efeb80b08f58~mv2.png"
FOOTER_ICON_URL = "https://static.wixstatic.com/media/da3421_111b24ae66f64f73aa94efeb80b08f58~mv2.png/v1/fit/w_2500,h_1330,al_c/da3421_111b24ae66f64f73aa94efeb80b08f58~mv2.png"
NO_STATS_AVAILABLE = "No stats recorded for that game yet"
FIND_PAST_STATS = "Stats of past games on: "
NEXT_MAP = "Next map"
CURRENT_MAP = "Current map"
VOTE = "vote(s)"
PLAYERS = "players"
ELAPSED_TIME = "Elapsed game time: "
ALLIED_PLAYERS = "Allied Players"
AXIS_PLAYERS = "Axis Players"
MATCH_SCORE_TITLE = "Match Score"
MATCH_SCORE = "Allied {0} : Axis {1}"
TIME_REMAINING = "Time Remaining"

SCOREBOARD_BASE_PATH = "/"
API_URL = ""
INFO_URL = ""


class section_enum(str, Enum):
    status = "status"
    status_no_pic = "status_no_pic"
    admin_links = "admin_links"
    admin_vips_admins = "admin_vips_admins"
    admin_auto_settings = "admin_auto_settings"
    map_info = "map_info"


class webhook_config(BaseModel):
    webhook_url: str = ""
    sections: List[section_enum]


class icons_config(BaseModel):
    offensive: str = "🟥"
    warfare: str = "🟩"
    skirmish: str = "🟨"
    dawn: str = "🌄"
    day: str = "⬜"
    dusk: str = "🌆"
    night: str = "🔳"
    overcast: str = "🌥️"
    rain: str = "☔"


class colors_config(BaseModel):
    blue: int = int("0x041E42", 16)
    red: int = int("0xBF0D3E", 16)
    embed: int = blue


class ServerstatusConfigType(TypedDict):
    enabled: bool

    author_name: str
    author_icon_url: str
    footer_icon_url: str
    next_map_text: str
    current_map_text: str
    players: str

    update_interval: int

    icons: icons_config

    colors: colors_config

    base_scoreboard_url: HttpUrl
    base_api_url: HttpUrl

    admin_desc_text: str
    status_desc_text: str

    webhooks: List[webhook_config]


class ServerStatusUserConfig(BaseUserConfig):
    enabled: bool = Field(default=True)

    author_name: str = Field(default=AUTHOR_NAME)
    author_icon_url: str = Field(default=AUTHOR_ICON_URL)
    footer_icon_url: str = Field(default=FOOTER_ICON_URL)
    next_map_text: str = Field(default=NEXT_MAP)
    current_map_text: str = Field(default=CURRENT_MAP)
    players: str = Field(default=PLAYERS)

    update_interval: int = Field(ge=1, default=5)

    icons: icons_config = Field(default_factory=icons_config)

    colors: colors_config = Field(default_factory=colors_config)

    base_scoreboard_url: Optional[HttpUrl] = Field(default=None)
    base_api_url: Optional[HttpUrl] = Field(
        default=f"http://frontend_{get_server_number()}/"
    )

    admin_desc_text: str = Field(default="")
    status_desc_text: str = Field(default="")

    webhooks: List[webhook_config] = Field(default_factory=list)

    @field_serializer("base_api_url", "base_scoreboard_url")
    def serialize_server_url(self, url: HttpUrl, _info):
        if url is not None:
            return str(url)
        else:
            return None

    @property
    def api_url(self) -> str:
        if not self.base_api_url:
            raise ValueError("base API URL not set")

        if str(self.base_api_url).endswith("/"):
            api_url = str(self.base_api_url)[:-1]
        else:
            api_url = str(self.base_api_url)

        validated_url = TypeAdapter(AnyHttpUrl).validate_python(api_url + API_ENDPOINT)
        return validated_url

    @property
    def stats_url(self) -> str:
        if not self.base_api_url:
            raise ValueError("base API URL not set")

        if str(self.base_api_url).endswith("/"):
            api_url = str(self.base_api_url)[:-1]
        else:
            api_url = str(self.base_api_url)

        validated_url: str = TypeAdapter(AnyHttpUrl).validate_python(
            api_url + STATS_ENDPOINT
        )
        return validated_url

    @property
    def info_url(self) -> str:
        if not self.base_api_url:
            raise ValueError("base API URL not set")

        if str(self.base_api_url).endswith("/"):
            api_url = str(self.base_api_url)[:-1]
        else:
            api_url = str(self.base_api_url)

        validated_url = TypeAdapter(AnyHttpUrl).validate_python(api_url + INFO_ENDPOINT)
        return validated_url

    @property
    def past_games_url(self) -> str:
        if not self.base_scoreboard_url:
            raise ValueError("base scoreboard URL not set")

        if str(self.base_scoreboard_url).endswith("/"):
            scoreboard_url = str(self.base_scoreboard_url)[:-1]
        else:
            scoreboard_url = str(self.base_scoreboard_url)

        validated_url = TypeAdapter(AnyHttpUrl).validate_python(
            scoreboard_url + PAST_GAMES_ENDPOINT
        )
        return validated_url

    @property
    def scoreboard_url(self) -> str:
        if not self.base_scoreboard_url:
            raise ValueError("base scoreboard URL not set")

        if str(self.base_scoreboard_url).endswith("/"):
            scoreboard_url = str(self.base_scoreboard_url)[:-1]
        else:
            scoreboard_url = str(self.base_scoreboard_url)

        validated_url = TypeAdapter(AnyHttpUrl).validate_python(
            scoreboard_url + SCOREBOARD_BASE_PATH
        )
        return validated_url

    @staticmethod
    def save_to_db(values: ServerstatusConfigType, dry_run=False):
        key_check(ServerstatusConfigType.__required_keys__, values.keys())

        validated_conf = ServerStatusUserConfig(
            enabled=values.get("enabled"),
            author_name=values.get("author_name"),
            author_icon_url=values.get("author_icon_url"),
            footer_icon_url=values.get("footer_icon_url"),
            next_map_text=values.get("next_map_text"),
            current_map_text=values.get("current_map_text"),
            players=values.get("players"),
            update_interval=values.get("update_interval"),
            icons=values.get("icons"),
            colors=values.get("colors"),
            base_api_url=values.get("base_api_url"),
            base_scoreboard_url=values.get("base_scoreboard_url"),
            admin_desc_text=values.get("admin_desc_text"),
            status_desc_text=values.get("status_desc_text"),
            webhooks=values.get("webhooks"),
        )

        if not dry_run:
            set_user_config(validated_conf.KEY(), validated_conf.model_dump())
