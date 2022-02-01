from os.path import expanduser

from pydantic import parse_file_as

from .config import BaseConfig

CONFIG_FILE = expanduser('~/config.json')
try:
    Config: BaseConfig = parse_file_as(BaseConfig, CONFIG_FILE)
except FileNotFoundError:
    try:
        CONFIG_FILE = './config.json'
        Config: BaseConfig = parse_file_as(BaseConfig, CONFIG_FILE)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to find config in {expanduser('~')} and .")

__all__ = ['Config']
