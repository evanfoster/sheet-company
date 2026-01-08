import typing
from pathlib import Path

import xdg_base_dirs
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=xdg_base_dirs.xdg_config_home() / "sheet-company" / "settings.yaml"
    )
    default_version: typing.Literal[
        "v40", "v49", "v50", "v56", "v62", "v69", "v72", "v73"
    ] = "v73"
    default_target_quota: int = 21
    default_quota_chance_amount: int = 17000
    should_write_overlay: bool = False
    overlay_output_path: Path = (
        xdg_base_dirs.xdg_cache_home() / "sheet-company" / "overlay"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)
