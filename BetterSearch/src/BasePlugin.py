from typing import List, Any
from base_plugin import BasePlugin
from . import main


class BetterSearchPlugin(BasePlugin):
    def on_plugin_load(self):
        main.initPlugin(self)

    def updateQuery(self, query: str):
        main.updateQuery(self, query)

    def on_plugin_unload(self):
        from .runtime import unloader
        unloader.teardown(self)

    def on_settings_changed(self, key, value):
        main.onSettingsChanged(self, key, value)

    def create_settings(self) -> List[Any]:
        return main.createSettings(self)

    def _onSourceCodeClick(self, view):
        main.onSourceCodeClick(self, view)
