import json
import os
from hook_utils import find_class
from android_utils import log
from file_utils import get_plugins_dir
from ..searchlib import SearchLib
from ..dbg import dbg as _dbg

_searchLib: SearchLib = None

def getSoPath() -> str:
    return os.path.join(get_plugins_dir(), "ElyxPlugins", "shareui_bettersearch", "BetterSearch", "native", "engine.so")

def initLib(plugin) -> bool:
    global _searchLib
    soPath = getSoPath()
    _dbg(f"bettersearch: loading .so from {soPath}", plugin)
    try:
        _searchLib = SearchLib(soPath)
        _dbg("bettersearch: library loaded successfully", plugin)
        return True
    except Exception as e:
        log(f"bettersearch: failed to load .so: {e}")
        return False

def getLib() -> SearchLib:
    return _searchLib

def rebuildIndex(plugin, pluginsControllerClass) -> None:
    global _searchLib
    try:
        controller = pluginsControllerClass.getInstance()
        pluginsMap = controller.plugins
        entries = []
        for key in pluginsMap.keySet().toArray():
            p = pluginsMap.get(key)
            if p is None:
                continue
            entries.append({
                "id": str(p.getId()),
                "name": str(p.getName()),
                "author": str(p.getAuthor()),
                "about": [str(p.getDescription()), str(p.getDescription())]
            })
        _dbg(f"bettersearch: building index for {len(entries)} plugins", plugin)
        _searchLib.buildIndex(json.dumps(entries), plugin)
    except Exception as e:
        log(f"bettersearch: index rebuild failed: {e}")

def setupHooks(plugin) -> None:
    from ..hooks.PluginCell import FillItemsHook, QueryHook
    from ..hooks.ChatActivity import SearchTextChangedHook, SearchCollapseHook, SearchAdapterNotifyHook
    from ..hooks.FragmentSearchField import DialogsSearchTextHook, DialogsSearchCollapseHook, DialogsAdapterNotifyHook
    _hookFilter(plugin)
    _hookQuery(plugin, QueryHook)
    _hookChatSearch(plugin, SearchTextChangedHook, SearchCollapseHook)
    _hookChatSearchAdapter(plugin, SearchAdapterNotifyHook)
    _hookDialogsText(plugin, DialogsSearchTextHook)
    _hookDialogsNotify(plugin, DialogsAdapterNotifyHook)

def _hookFilter(plugin) -> None:
    try:
        actClass = find_class("com.exteragram.messenger.plugins.ui.PluginsActivity")
        if not actClass:
            log("bettersearch: PluginsActivity not found")
            return
        from ..hooks.PluginCell import FillItemsHook
        results = plugin.hook_all_methods(actClass, "fillItems", FillItemsHook(plugin))
        _dbg(f"bettersearch: hook_all_methods(fillItems) returned {results}", plugin)
    except Exception as e:
        log(f"bettersearch: filter hook failed: {e}")

def _hookQuery(plugin, QueryHook) -> None:
    try:
        listenerClass = find_class("com.exteragram.messenger.plugins.ui.PluginsActivity$1")
        if not listenerClass:
            log("bettersearch: PluginsActivity$1 not found")
            return
        results = plugin.hook_all_methods(listenerClass, "onTextChanged", QueryHook(plugin))
        _dbg(f"bettersearch: hook_all_methods(PluginsActivity$1.onTextChanged) returned {results}", plugin)
    except Exception as e:
        log(f"bettersearch: query hook failed: {e}")

def _hookChatSearch(plugin, SearchTextChangedHook, SearchCollapseHook) -> None:
    try:
        listenerClass = find_class("org.telegram.ui.ChatActivity$SearchItemListener")
        if not listenerClass:
            log("bettersearch: ChatActivity$SearchItemListener not found")
            return
        results = plugin.hook_all_methods(listenerClass, "onTextChanged", SearchTextChangedHook(plugin))
        _dbg(f"bettersearch: hooked ChatActivity SearchItemListener.onTextChanged: {results}", plugin)
        results = plugin.hook_all_methods(listenerClass, "onSearchCollapse", SearchCollapseHook(plugin))
        _dbg(f"bettersearch: hooked ChatActivity SearchItemListener.onSearchCollapse: {results}", plugin)
    except Exception as e:
        log(f"bettersearch: chat search hook failed: {e}")

def _hookChatSearchAdapter(plugin, SearchAdapterNotifyHook) -> None:
    try:
        adapterClass = find_class("org.telegram.ui.Adapters.MessagesSearchAdapter")
        if not adapterClass:
            log("bettersearch: MessagesSearchAdapter not found")
            return
        results = plugin.hook_all_methods(adapterClass, "notifyDataSetChanged", SearchAdapterNotifyHook(plugin))
        _dbg(f"bettersearch: hooked MessagesSearchAdapter.notifyDataSetChanged: {results}", plugin)
    except Exception as e:
        log(f"bettersearch: chat search adapter hook failed: {e}")

def _hookDialogsText(plugin, DialogsSearchTextHook) -> None:
    # afterTextChanged is declared in SearchTextWatcher directly
    try:
        watcherClass = find_class("org.telegram.messenger.utils.SearchTextWatcher")
        if not watcherClass:
            log("bettersearch: SearchTextWatcher not found")
            return
        results = plugin.hook_all_methods(watcherClass, "afterTextChanged", DialogsSearchTextHook(plugin))
        log(f"bettersearch: hooked SearchTextWatcher.afterTextChanged: {results}")
    except Exception as e:
        log(f"bettersearch: dialogs text hook failed: {e}")

def _hookDialogsNotify(plugin, DialogsAdapterNotifyHook) -> None:
    try:
        adapterClass = find_class("org.telegram.ui.Adapters.DialogsSearchAdapter")
        if not adapterClass:
            log("bettersearch: DialogsSearchAdapter not found")
            return
        # updateSearchResults
        results = plugin.hook_all_methods(adapterClass, "updateSearchResults", DialogsAdapterNotifyHook(plugin))
        log(f"bettersearch: hooked DialogsSearchAdapter.updateSearchResults: {results}")
    except Exception as e:
        log(f"bettersearch: dialogs notify hook failed: {e}")
