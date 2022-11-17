"""
A module for OpenDota constants caching functions.
"""
import os
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from functools import partial, wraps
from pathlib import Path
from typing import Final, ParamSpec, TypeVar
from urllib.error import HTTPError
from urllib.request import urlopen

import simdjson
from simdjson import Parser

T = TypeVar("T")
P = ParamSpec("P")

HOME_DIR: Final[Path] = Path(__file__).resolve().parents[1]
CONSTANTS_URL: Final[
    str
] = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/"


def enter_subdir(subdir: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """During the execution of a function, temporarily enter a subdirectory."""

    def decorator(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args, **kwargs) -> T:
            old_dir, new_dir = Path.cwd(), HOME_DIR / subdir
            new_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(new_dir)
            return_value = function(*args, **kwargs)
            os.chdir(old_dir)
            return return_value

        return wrapper

    return decorator


def make_update_timestamp(filename: str, patch: str, days: int = 2) -> None:
    """Set the time threshold at which the cache timestamp has to be checked."""
    timestamp = datetime.now() + timedelta(days=days)
    timestamp = simdjson.dumps({"timestamp": timestamp.isoformat(), "patch": patch})
    with open(filename, "w", encoding="utf-8") as file:
        file.write(timestamp)


def get_latest_patch() -> str:
    """Get the latest available DotA 2 patch."""
    with urlopen(CONSTANTS_URL + "patchnotes.json") as patchnotes_link:
        *_, patch = Parser().parse(patchnotes_link.read()).keys()
    return patch


@enter_subdir("cache")
def get_cooldowns(
    constant_type: str, item_or_ability: str | None, force_update: bool
) -> str | Iterable[str]:
    """A shorthand for querying cooldowns from the OpenDota constants database. To
    reduce the load on GitHub servers and waste less traffic, queries are cached and
    are updated when there is a new patch only. Caching is done with simdjson, an
    extremely fast JSON parser."""
    if item_or_ability is None:
        raise ValueError(
            f"Missing item or ability command line parameter for constant type "
            f"{constant_type}."
        )
    data, patch, timestamp_filename, cache_filename = (
        {},
        None,
        constant_type + "_timestamp.json",
        constant_type + "_cache.json",
    )
    update_timestamp = partial(make_update_timestamp, timestamp_filename)
    try:
        assert not force_update
        # Check whether the locally stored cache needs an update
        timestamp = Parser().load(timestamp_filename)
        # Only prune cache if new patch has been released
        if datetime.now() > datetime.fromisoformat(timestamp["timestamp"]):
            patch = get_latest_patch()
            assert patch == timestamp["patch"]
            update_timestamp(patch)
        # Load the locally stored cache, if it exists
        data = Parser().load(cache_filename)
    except (FileNotFoundError, OSError, AssertionError, KeyError):
        with urlopen(CONSTANTS_URL + constant_type + ".json") as opendota_link:
            try:
                data = Parser().parse(opendota_link.read())
            except HTTPError as error:
                raise ValueError(
                    f'Constant type "{constant_type}" does not exist in '
                    f"the OpenDotA constants database."
                ) from error
        if patch is None:
            patch = get_latest_patch()
        update_timestamp(patch)
        with open(cache_filename, "wb") as file:
            file.write(data.mini)  # NOQA
    try:
        return data[item_or_ability]["cd"]
    except KeyError as error:
        raise KeyError(
            "This ability or item does not exist in the OpenDotA constants "
            "database, or it doesn't have a cooldown. Maybe you misspelled it? "
            "Make sure to prefix the hero name for abilities "
            "(e.g. `faceless_void_chronosphere`)."
        ) from error
