from base_plugin import MethodHook
from hook_utils import get_private_field
from android_utils import log
from ..dbg import dbg as _dbg

MIN_QUERY_LEN = 2
MIN_SCORE = 0.25

class DialogsSearchTextHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        try:
            editable = param.args[0]
            query = str(editable) if editable is not None else ""
            if self._pluginRef.dialogsSearchQuery != query:
                # new query
                self._pluginRef.dialogsTranslitPending = False
            self._pluginRef.dialogsSearchQuery = query
            log(f"bettersearch [dialogs]: text hook fired, query={repr(query)}")
        except Exception as e:
            log(f"bettersearch [dialogs]: DialogsSearchTextHook failed: {e}")


class DialogsSearchCollapseHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        self._pluginRef.dialogsSearchQuery = None
        self._pluginRef.dialogsTranslitPending = False
        _dbg("bettersearch [dialogs]: search collapsed, query cleared", self._pluginRef)


class DialogsAdapterNotifyHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        # updateSearchResults(ArrayList result, ArrayList names, ArrayList encUsers, ArrayList contacts, int searchId)
        if not getattr(self._pluginRef, "_enableDialogsSearch", True):
            return
        query = getattr(self._pluginRef, "dialogsSearchQuery", None)
        if not query or len(query) < MIN_QUERY_LEN:
            return

        log(f"bettersearch [dialogs]: updateSearchResults fired, query={repr(query)}")
        try:
            from ..runtime.loader import getLib
            lib = getLib()
            if lib is None:
                log("bettersearch [dialogs]: lib is None, skipping")
                return

            resultList = param.args[0]
            log(f"bettersearch [dialogs]: resultList type={type(resultList).__name__ if resultList is not None else 'None'}")
            if resultList is None:
                return

            size = resultList.size()
            log(f"bettersearch [dialogs]: resultList.size()={size}")
            if size == 0:
                log(f"bettersearch [dialogs]: empty results, entering _tryTranslit for q={repr(query)}")
                self._tryTranslit(query, param.thisObject)
                return
            _dbg(f"bettersearch [dialogs]: scoring {size} items for q={repr(query)}", self._pluginRef)

            scored = []
            for i in range(size):
                item = resultList.get(i)
                name = ""
                username = ""
                about = ""
                try:
                    nameVal = item.name if hasattr(item, "name") else None
                    if nameVal is not None:
                        name = str(nameVal)
                    unVal = item.username if hasattr(item, "username") else None
                    if unVal is not None:
                        username = str(unVal)
                    aboutVal = item.about if hasattr(item, "about") else None
                    if aboutVal is not None:
                        about = str(aboutVal)
                except Exception:
                    pass
                score = lib.dialogScore(name, username, about, query)
                scored.append((score, item, name or username))
                _dbg(f"bettersearch [dialogs]:   [{i}] name={repr(name)} score={score:.3f}", self._pluginRef)

            aboveThreshold = [x for x in scored if x[0] >= MIN_SCORE]
            if not aboveThreshold:
                _dbg(f"bettersearch [dialogs]: all scores below {MIN_SCORE}, skipping reorder", self._pluginRef)
                return

            scored.sort(key=lambda x: -x[0])
            for j, (score, item, label) in enumerate(scored):
                try:
                    resultList.set(j, item)
                except Exception as e:
                    log(f"bettersearch [dialogs]: set failed at {j}: {e}")
                    return

            top3 = [f"{label}({s:.2f})" for (s, _, label) in scored[:3]]
            _dbg(f"bettersearch [dialogs]: reordered {size} dialogs, top3={top3}", self._pluginRef)
        except Exception as e:
            log(f"bettersearch [dialogs]: DialogsAdapterNotifyHook failed: {e}")

    def _tryTranslit(self, query: str, adapter):
        log(f"bettersearch [dialogs]: _tryTranslit called, pending={getattr(self._pluginRef, 'dialogsTranslitPending', False)}, q={repr(query)}")
        if getattr(self._pluginRef, "dialogsTranslitPending", False):
            self._pluginRef.dialogsTranslitPending = False
            log("bettersearch [dialogs]: translit retry also empty, giving up")
            return
        try:
            from ..searchlib import looksLikeWrongLayout, fixLayout
            looks = looksLikeWrongLayout(query)
            log(f"bettersearch [dialogs]: looksLikeWrongLayout={looks}")
            if not looks:
                return
            fixed = fixLayout(query)
            log(f"bettersearch [dialogs]: fixLayout result={repr(fixed)}")
            if fixed == query:
                log("bettersearch [dialogs]: fixed == query, skipping")
                return
            log(f"bettersearch [dialogs]: retrying with translit {repr(query)} -> {repr(fixed)}")
            self._pluginRef.dialogsTranslitPending = True
            self._pluginRef.dialogsSearchQuery = fixed
            self._retrySearch(fixed, adapter)
        except Exception as e:
            log(f"bettersearch [dialogs]: _tryTranslit failed: {e}")

    def _retrySearch(self, fixedQuery: str, adapter):
        try:
            from android_utils import run_on_ui_thread
            folderId = get_private_field(adapter, "folderId")
            log(f"bettersearch [dialogs]: _retrySearch folderId={folderId} q={repr(fixedQuery)}")
            if folderId is None:
                folderId = 0
            run_on_ui_thread(lambda: adapter.searchDialogs(fixedQuery, folderId, True))
        except Exception as e:
            log(f"bettersearch [dialogs]: _retrySearch failed: {e}")
