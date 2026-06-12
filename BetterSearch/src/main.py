from typing import List, Any
from hook_utils import find_class
from android_utils import log
from elyx import strings
from .searchlib import isRussian
from .settings import buildSettingsList, SOURCE_URL
from .runtime import loader, unloader
from .dbg import dbg as _dbg


def initPlugin(plugin) -> None:
    if not loader.initLib(plugin):
        return
    plugin.currentQuery = None
    plugin.lastMatchIds = None
    plugin.chatSearchQuery = None
    plugin.chatTranslitPending = False
    plugin.dialogsSearchQuery = None
    plugin.dialogsTranslitPending = False
    plugin._improvePluginsSearch = plugin.get_setting("improve_plugins_search", True)
    plugin._enableChatSearch = plugin.get_setting("enable_chat_search", True)
    plugin._enableDialogsSearch = plugin.get_setting("enable_dialogs_search", True)
    plugin._pluginsControllerClass = find_class("com.exteragram.messenger.plugins.PluginsController")
    _dbg(f"bettersearch: PluginsController cached: {plugin._pluginsControllerClass is not None}", plugin)
    loader.rebuildIndex(plugin, plugin._pluginsControllerClass)
    _dbg("bettersearch: starting hook setup", plugin)
    loader.setupHooks(plugin)
    _dbg("bettersearch: hook setup done", plugin)


def updateQuery(plugin, query: str) -> None:
    _dbg(f"bettersearch: updateQuery called with q={repr(query)}", plugin)
    plugin.currentQuery = query
    if not query:
        _dbg("bettersearch: empty query, clearing match filter", plugin)
        plugin.lastMatchIds = None
        return
    lib = loader.getLib()
    ids = lib.query(query, isRussian(query), plugin)
    if len(ids) == 0 and len(query) > 2:
        for trimLen in range(len(query) - 1, 2, -1):
            prefix = query[:trimLen]
            ids = lib.query(prefix, isRussian(prefix), plugin)
            _dbg(f"bettersearch: prefix fallback q={repr(prefix)} -> {len(ids)} results", plugin)
            if len(ids) > 0:
                break
    plugin.lastMatchIds = ids
    _dbg(f"bettersearch: lastMatchIds updated ({len(ids)} items): {ids}", plugin)


def onSettingsChanged(plugin, key: str, value) -> None:
    if key == "improve_plugins_search":
        plugin._improvePluginsSearch = value
    elif key == "enable_chat_search":
        plugin._enableChatSearch = value
    elif key == "enable_dialogs_search":
        plugin._enableDialogsSearch = value


def createSettings(plugin) -> List[Any]:
    return buildSettingsList(plugin)


def onSourceCodeClick(plugin, view) -> None:
    try:
        from android.content import Intent
        from android.net import Uri
        from org.telegram.messenger import ApplicationLoader
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(SOURCE_URL))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ApplicationLoader.applicationContext.startActivity(intent)
    except Exception as e:
        log(f"bettersearch: open source url failed: {e}")
