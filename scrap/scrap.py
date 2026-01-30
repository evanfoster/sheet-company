import json
import typing
from pathlib import Path

import pydantic

import base
import lc_types
import util


class ScrapItem(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(validate_by_name=True)
    model_name: str = pydantic.Field(validation_alias="mName")
    name: str
    weight: int | float
    conductive: bool
    two_handed: bool = pydantic.Field(validation_alias="twoHanded")
    minimum_raw_value: int = pydantic.Field(validation_alias="minValue")
    maximum_raw_value: int = pydantic.Field(validation_alias="maxValue")
    is_weapon: bool = pydantic.Field(validation_alias="isWeapon")
    has_battery: bool = pydantic.Field(validation_alias="hasBattery")

    @staticmethod
    def _divide_value(value) -> int | float:
        divided = value / 2.5
        if divided.is_integer():
            return int(divided)
        return divided

    @property
    def min_value(self) -> int | float:
        return self._divide_value(self.minimum_raw_value)

    @property
    def max_value(self) -> int | float:
        return self._divide_value(self.maximum_raw_value)


class Scrap(base.BaseLCData[ScrapItem]):
    @classmethod
    def wiki_page_base(cls) -> str:
        return "Module:Scraps/Data"

    @classmethod
    def data_path(cls) -> Path:
        return util.get_script_dir(__file__) / "data"

    @classmethod
    def parse_wiki_data(cls, data: str, version: lc_types.Versions) -> typing.Self:
        output_model = cls(version=version)
        parsed = util.wiki_data_parser(data)
        parsed_data = parsed.get("data")
        if parsed_data is None:
            raise RuntimeError("Failed to get data from wiki")
        assert isinstance(parsed_data, dict)
        for parsed_item in parsed_data.values():
            scrap_item = ScrapItem(**parsed_item)
            output_model.items[scrap_item.name] = scrap_item
            output_model.name_mapping[scrap_item.model_name] = scrap_item.name
        return output_model

    @classmethod
    def get_scrap_for_version(cls, version: lc_types.Versions):
        data = json.loads(
            (util.get_script_dir(__file__) / "data" / version / "data.json").read_text()
        )
        return cls(**data)


if __name__ == "__main__":
    Scrap.get_data()
