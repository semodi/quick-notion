from pathlib import Path

import yaml
from pytion import Notion
from pytion.api import Element


def _load_config():
    config_loc = Path("~/.notion/config.yaml").expanduser().resolve()
    return yaml.safe_load(open(config_loc))


@lambda x: x()
class Connection:
    def __init__(self):
        self.config = _load_config()
        self._client = Notion(token=self.config["token"])

    def get_db(self, mode: str) -> Element:
        return self._client.databases.get(self.config["databases"][mode])

    @property
    def client(self):
        return self._client
