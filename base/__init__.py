import json
import typing
from abc import ABC, abstractmethod
from pathlib import Path

import httpx
import pydantic

from lc_types import Versions


class BaseLCData[T](pydantic.BaseModel, ABC):
    items: dict[str, T] = pydantic.Field(default_factory=dict)
    name_mapping: dict[str, str] = pydantic.Field(default_factory=dict)
    wiki_api_uri: typing.ClassVar[str] = "https://lethal.miraheze.org/w/api.php"

    @classmethod
    @abstractmethod
    def wiki_page_base(cls) -> str: ...

    @classmethod
    @abstractmethod
    def data_path(cls) -> Path: ...

    @classmethod
    @abstractmethod
    def parse_wiki_data(cls, data: str) -> typing.Self: ...

    def write_model(self, version: Versions):
        version_data_path = self.data_path() / version
        version_data_path.mkdir(parents=True, exist_ok=True)
        version_data_file = version_data_path / "data.json"
        version_data_file.write_text(self.model_dump_json())

    @classmethod
    def get_data(cls) -> None:
        versions = list(Versions.__members__.keys())
        query_parameters = {
            "action": "parse",
            "prop": "wikitext",
            "format": "json".strip(),
        }
        for version in versions:
            version = Versions(version)

            query_parameters["page"] = f"{cls.wiki_page_base()}/{version}"
            payload = (
                httpx.get(cls.wiki_api_uri, params=query_parameters)
                .raise_for_status()
                .json()
            )
            raw_data: str | None = (
                payload.get("parse", {}).get("wikitext", {}).get("*", None)
            )
            if raw_data is None:
                raise RuntimeError(f"Failed to get data for version {version}")
            output_model = cls.parse_wiki_data(raw_data)
            output_model.write_model(version)


    @classmethod
    def get_for_version(cls, version: Versions) -> typing.Self:
        data = json.loads(
            (cls.data_path() / "data" / version / "data.json").read_text()
        )
        return cls(**data)
