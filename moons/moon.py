import typing
from pathlib import Path

import pydantic

import base
import lc_types
import util


class Moon(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(validate_by_name=True)
    version: lc_types.Versions
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
    raw_max_scrap: int = pydantic.Field(alias="maxScrap")
    max_total_scrap_value: int = pydantic.Field(alias="maxTotalScrapValue")
    min_scrap: int = pydantic.Field(alias="minScrap")
    min_total_scrap_value: int = pydantic.Field(alias="minTotalScrapValue")
    name: str
    risk_level: str = pydantic.Field(alias="riskLevel")
    size_multiplier: float = pydantic.Field(alias="sizeMultiplier")
    spawn_enemies_and_scrap: bool = pydantic.Field(alias="spawnEnemiesAndScraps")
    raw_weather_types: dict[int, lc_types.Weathers] = pydantic.Field(
        alias="weatherTypes",
    )

    @property
    def weather_types(self) -> set[lc_types.Weathers]:
        return set(self.raw_weather_types.values()) | {
            lc_types.Weathers.clear,
        }

    @property
    def interiors(self) -> set[lc_types.Dungeons]:
        return set(self.dungeon_rarities.keys())

    @property
    def max_scrap(self) -> int:
        if (
            self.version >= lc_types.Versions.v61
            and lc_types.Dungeons.mineshaft in self.interiors
        ):
            # Naive, but it'll do for now.
            return self.raw_max_scrap + 6
        return self.raw_max_scrap

    @property
    def moon_cost(self) -> int:
        return lc_types.MoonCosts[self.name]


class Moons(base.BaseLCData[Moon]):
    @classmethod
    def wiki_page_base(cls) -> str:
        return "Module:Moons/Data"

    @classmethod
    def data_path(cls) -> Path:
        return util.get_script_dir(__file__) / "data"

    @classmethod
    def parse_wiki_data(cls, data: str, version: lc_types.Versions) -> typing.Self:
        output_model = cls(version=version)
        parsed = util.wiki_data_parser(data)
        parsed_data = parsed.get("data")
        assert isinstance(parsed_data, dict)
        if parsed_data is None:
            raise RuntimeError("Failed to get data from wiki")
        for parsed_item in parsed_data.values():
            moon = Moon(version=version, **parsed_item)
            output_model.items[moon.model_name.removesuffix("Level")] = moon
            output_model.name_mapping[moon.model_name] = moon.model_name.removesuffix(
                "Level"
            )
        return output_model

    @property
    def available_moons(self) -> set[str]:
        return set(self.items.keys())


if __name__ == "__main__":
    Moons.get_data()
