import typing
from pathlib import Path

import pydantic

import base
import lc_types
import util

class Moon(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(validate_by_name=True)
    daytime_spawn_deviation: int = pydantic.Field(alias="daytimeSpawnDeviation")
    dungeon_rarities: dict[lc_types.Dungeons, int] = pydantic.Field(
        alias="dungeonRarities", default={}
    )
    has_time: bool = pydantic.Field(alias="hasTime")
    indoor_spawn_deviation: int = pydantic.Field(alias="indoorSpawnDeviation")
    model_name: str = pydantic.Field(alias="mName")
    max_daytime_power_count: int = pydantic.Field(alias="maxDaytimePowerCount")
    max_outside_power_count: int = pydantic.Field(alias="maxOutsidePowerCount")
    max_power_count: int = pydantic.Field(alias="maxPowerCount")
    max_scrap: int = pydantic.Field(alias="maxScrap")
    max_total_scrap_value: int = pydantic.Field(alias="maxTotalScrapValue")
    min_scrap: int = pydantic.Field(alias="minScrap")
    min_total_scrap_value: int = pydantic.Field(alias="minTotalScrapValue")
    name: str
    risk_level: str = pydantic.Field(alias="riskLevel")
    size_multiplier: float = pydantic.Field(alias="sizeMultiplier")
    spawn_enemies_and_scrap: bool = pydantic.Field(alias="spawnEnemiesAndScraps")
    weather_types: dict[int, lc_types.Weathers] = pydantic.Field(alias="weatherTypes")


class Moons(base.BaseLCData[Moon]):
    @classmethod
    def wiki_page_base(cls) -> str:
        return "Module:Moons/Data"

    @classmethod
    def data_path(cls) -> Path:
        return util.get_script_dir(__file__) / "data"

    @classmethod
    def parse_wiki_data(cls, data: str) -> typing.Self:
        output_model = cls()
        parsed = util.wiki_data_parser(data)
        parsed_data = parsed.get("data")
        assert isinstance(parsed_data, dict)
        if parsed_data is None:
            raise RuntimeError("Failed to get data from wiki")
        for parsed_item in parsed_data.values():
            moon = Moon(**parsed_item)
            output_model.items[moon.model_name.removesuffix("Level")] = moon
            output_model.name_mapping[moon.model_name] = moon.model_name.removesuffix(
                "Level"
            )
        return output_model


if __name__ == "__main__":
    Moons.get_data()
