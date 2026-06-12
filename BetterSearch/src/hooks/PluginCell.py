from base_plugin import MethodHook
from hook_utils import get_private_field
from android_utils import log
from ..dbg import dbg as _dbg

class FillItemsHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef
        self._patchedPlugins = []

    def before_hooked_method(self, param):
        self._patchedPlugins = []
        if not self._pluginRef._improvePluginsSearch:
            return
        matchIds = self._pluginRef.lastMatchIds
        if matchIds is None:
            return

        try:
            activity = param.thisObject
            searching = get_private_field(activity, "searching")
            query = get_private_field(activity, "query")

            if not searching or not query:
                return

            queryLower = str(query).lower()
            matchIdsLower = {x.lower() for x in matchIds}
            _dbg(f"bettersearch: FillItemsHook before; query={repr(queryLower)} matchIds={len(matchIds)}", self._pluginRef)
            allPlugins = self._pluginRef._pluginsControllerClass.getInstance().plugins
            keysArray = allPlugins.keySet().toArray()

            for i in range(len(keysArray)):
                plugin = allPlugins.get(keysArray[i])
                if plugin is None:
                    continue
                if str(plugin.getId()).lower() not in matchIdsLower:
                    continue
                try:
                    nameField = plugin.getClass().getDeclaredField("name")
                    nameField.setAccessible(True)
                    originalName = nameField.get(plugin)
                    nameField.set(plugin, f"{originalName} {queryLower}")
                    self._patchedPlugins.append((plugin, nameField, str(originalName)))
                    _dbg(f"bettersearch: patched name for {plugin.getId()}", self._pluginRef)
                except Exception as e:
                    _dbg(f"bettersearch: patch failed for {plugin.getId()}: {e}", self._pluginRef)
        except Exception as e:
            _dbg(f"bettersearch: FillItemsHook before failed: {e}", self._pluginRef)

    def after_hooked_method(self, param):
        for plugin, nameField, originalName in self._patchedPlugins:
            try:
                nameField.set(plugin, originalName)
            except Exception as e:
                _dbg(f"bettersearch: restore name failed: {e}", self._pluginRef)
        _dbg(f"bettersearch: FillItemsHook after; restored {len(self._patchedPlugins)} plugin names", self._pluginRef)
        self._patchedPlugins = []

        matchIds = self._pluginRef.lastMatchIds
        if not matchIds:
            return

        try:
            activity = param.thisObject
            searching = get_private_field(activity, "searching")
            query = get_private_field(activity, "query")
            if not searching or not query:
                return

            arrayList = param.args[0]
            self._reorderByScore(arrayList, matchIds)
        except Exception as e:
            _dbg(f"bettersearch: reorder failed: {e}", self._pluginRef)

    def _reorderByScore(self, arrayList, matchIds):
        scoreMap = {mid.lower(): i for i, mid in enumerate(matchIds)}

        pairs = []
        size = arrayList.size()
        i = 0
        while i < size:
            item = arrayList.get(i)
            plugin = None
            try:
                plugin = item.object
            except Exception:
                pass
            if plugin is not None:
                try:
                    pluginId = str(plugin.getId())
                    from com.exteragram.messenger.plugins import PluginsController
                    if not PluginsController.isPluginPinned(pluginId):
                        score = scoreMap.get(pluginId.lower(), len(matchIds))
                        spaceIdx = i + 1 if (i + 1 < size) else -1
                        pairs.append((i, spaceIdx, pluginId, score))
                except Exception as e:
                    _dbg(f"bettersearch: reorder item error: {e}", self._pluginRef)
            i += 1

        if len(pairs) <= 1:
            return

        alreadySorted = all(pairs[j][3] <= pairs[j + 1][3] for j in range(len(pairs) - 1))
        if alreadySorted:
            return

        sortedPairs = sorted(pairs, key=lambda x: x[3])

        allIndices = []
        for pluginIdx, spaceIdx, _, _ in pairs:
            allIndices.append(pluginIdx)
            if spaceIdx != -1:
                allIndices.append(spaceIdx)
        allIndices.sort()

        replacement = []
        for pluginIdx, spaceIdx, _, _ in sortedPairs:
            replacement.append(arrayList.get(pluginIdx))
            if spaceIdx != -1:
                replacement.append(arrayList.get(spaceIdx))

        for j, listIdx in enumerate(allIndices):
            if j < len(replacement):
                try:
                    arrayList.set(listIdx, replacement[j])
                except Exception as e:
                    _dbg(f"bettersearch: arrayList.set failed at {listIdx}: {e}", self._pluginRef)
                    return

        _dbg(f"bettersearch: reordered {len(pairs)} plugins by score", self._pluginRef)


class QueryHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        editText = param.args[0]
        query = str(editText.getText()) if editText is not None else ""
        _dbg(f"bettersearch: QueryHook fired, query={repr(query)}", self._pluginRef)
        if not self._pluginRef._improvePluginsSearch:
            self._pluginRef.lastMatchIds = None
            return
        self._pluginRef.updateQuery(query)
