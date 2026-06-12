from typing import Any, List
from ui.settings import Header, Text, Divider, Switch
from elyx import strings

SOURCE_URL = "https://github.com/shareui/better-search"

def buildSettingsList(plugin) -> List[Any]:
    return [
        Header(text=strings["SETTINGS_TITLE"]),
        Switch(
            key="improve_plugins_search",
            text=strings["IMPROVE_PLUGINS_SEARCH"],
            icon="msg_plugins",
            default=True,
        ),
        Switch(
            key="enable_chat_search",
            text=strings["ENABLE_CHAT_SEARCH"],
            icon="msg_msgbubble2",
            default=True,
        ),
        Switch(
            key="enable_dialogs_search",
            text=strings["ENABLE_DIALOGS_SEARCH"],
            icon="msg_search",
            default=True,
        ),
        Divider(),
        Header(text=strings["MISC_HEADER"]),
        Switch(
            key="debug_logs",
            text=strings["DEBUG_LOGS"],
            subtext=strings["DEBUG_LOGS_SUB"],
            icon="msg_log",
            default=False,
        ),
        Text(
            text=strings["SOURCE_CODE"],
            icon="msg_link2",
            on_click=plugin._onSourceCodeClick
        ),
        Divider(text=strings["CHANNEL_NOTE"]),
    ]
