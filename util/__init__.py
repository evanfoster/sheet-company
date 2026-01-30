import collections.abc
import typing
from pathlib import Path

# This library has _zero_ type stubs
import lupa.lua54 as lupa  # type: ignore


# Thanks, rtaft!
# https://stackoverflow.com/a/45846841
def human_format(num: int | float) -> str:
    num = float("{:.3g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return "{}{}".format(
        "{:f}".format(num).rstrip("0").rstrip("."), ["", "K", "M", "B", "T"][magnitude]
    )


def strtobool(val: str) -> bool | None:
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Returns None if
    'val' is anything else.
    This _was_ in distutils.util, but that was removed in Python 3.12. Rest in peace,
    strtobool. I'm going to change it to be a little less annoying, though.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        return None


def get_script_dir(file: str) -> Path:
    return Path(file).resolve().parent


def recursive_cast(table: typing.Any) -> collections.abc.MutableMapping:
    as_dict = dict(table)
    for key, value in as_dict.items():
        if lupa.lua_type(value) == "table":
            as_dict[key] = recursive_cast(value)
    return as_dict


def get_lua_runtime() -> lupa.LuaRuntime:
    lua = lupa.LuaRuntime(max_memory=500000)  # 500K of memory _should_ be enough?
    # Basic attempt to make this less terrifying
    for key in list(lua.globals()):
        if key != "_G":
            del lua.globals()[key]
    return lua


def wiki_data_parser(
    lua_script: str,
) -> collections.abc.MutableMapping[str, str | int | float | bool | list | dict]:
    lua = get_lua_runtime()
    data = lua.execute(lua_script)
    return recursive_cast(data)
