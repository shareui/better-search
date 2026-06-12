from base_plugin import MethodHook
from hook_utils import get_private_field
from android_utils import log
from ..dbg import dbg as _dbg

MIN_QUERY_LEN = 2
MIN_SCORE = 0.2

class SearchTextChangedHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        try:
            editText = param.args[0]
            query = str(editText.getText()) if editText is not None else ""
            if self._pluginRef.chatSearchQuery != query:
                # new query
                self._pluginRef.chatTranslitPending = False
            self._pluginRef.chatSearchQuery = query
            _dbg(f"bettersearch [chat]: hook fired, query={repr(query)}", self._pluginRef)
        except Exception as e:
            log(f"bettersearch [chat]: SearchTextChangedHook failed: {e}")


class SearchCollapseHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        self._pluginRef.chatSearchQuery = None
        self._pluginRef.chatTranslitPending = False
        _dbg("bettersearch [chat]: search collapsed, query cleared", self._pluginRef)


class SearchAdapterNotifyHook(MethodHook):
    def __init__(self, pluginRef):
        self._pluginRef = pluginRef

    def after_hooked_method(self, param):
        if not getattr(self._pluginRef, "_enableChatSearch", True):
            return
        query = getattr(self._pluginRef, "chatSearchQuery", None)
        if not query or len(query) < MIN_QUERY_LEN:
            return
        try:
            from ..runtime.loader import getLib
            lib = getLib()
            if lib is None:
                return

            adapter = param.thisObject
            resultList = get_private_field(adapter, "searchResultMessages")
            if resultList is None:
                return
            
            size = resultList.size()
            if size == 0:
                _dbg(f"bettersearch [chat]: no results for q={repr(query)}", self._pluginRef)
                self._tryTranslit(query)
                return

            _dbg(f"bettersearch [chat]: scoring {size} messages for q={repr(query)}", self._pluginRef)
            scored = []
            for i in range(size):
                msg = resultList.get(i)
                text = ""
                try:
                    owner = msg.messageOwner
                    if owner is not None and owner.message is not None:
                        text = str(owner.message)
                except Exception:
                    pass
                score = lib.msgScore(text, query)
                scored.append((score, msg))

            aboveThreshold = [x for x in scored if x[0] >= MIN_SCORE]
            if not aboveThreshold:
                _dbg(f"bettersearch [chat]: all scores below {MIN_SCORE}, skipping reorder", self._pluginRef)
                return

            scored.sort(key=lambda x: -x[0])
            for j, (score, msg) in enumerate(scored):
                try:
                    resultList.set(j, msg)
                except Exception as e:
                    log(f"bettersearch [chat]: set failed at {j}: {e}")
                    return

            top3 = [f"{s:.2f}" for (s, _) in scored[:3]]
            _dbg(f"bettersearch [chat]: reordered {size} messages, top3 scores={top3}", self._pluginRef)
        except Exception as e:
            log(f"bettersearch [chat]: SearchAdapterNotifyHook failed: {e}")

    def _tryTranslit(self, query: str):
        if getattr(self._pluginRef, "chatTranslitPending", False):
            self._pluginRef.chatTranslitPending = False
            _dbg(f"bettersearch [chat]: translit retry also empty, giving up", self._pluginRef)
            return
        try:
            from ..searchlib import looksLikeWrongLayout, fixLayout
            if not looksLikeWrongLayout(query):
                return
            fixed = fixLayout(query)
            if fixed == query:
                return
            _dbg(f"bettersearch [chat]: retrying with translit {repr(query)} -> {repr(fixed)}", self._pluginRef)
            self._pluginRef.chatTranslitPending = True
            self._pluginRef.chatSearchQuery = fixed
            self._retrySearch(fixed)
        except Exception as e:
            log(f"bettersearch [chat]: _tryTranslit failed: {e}")

    def _retrySearch(self, fixedQuery: str):
        try:
            from client_utils import get_media_data_controller, get_notification_center, run_on_queue, PLUGINS_QUEUE
            from android_utils import run_on_ui_thread
            mdc = get_media_data_controller()
            dialogId = get_private_field(mdc, "lastDialogId")
            mergeDialogId = get_private_field(mdc, "lastMergeDialogId")
            guid = get_private_field(mdc, "lastGuid")
            replyMessageId = get_private_field(mdc, "lastReplyMessageId")
            user = get_private_field(mdc, "lastSearchUser")
            chat = get_private_field(mdc, "lastSearchChat")
            reaction = get_private_field(mdc, "lastReaction")
            if dialogId is None or guid is None:
                _dbg("bettersearch [chat]: _retrySearch: missing lastDialogId/lastGuid", self._pluginRef)
                return
            _dbg(f"bettersearch [chat]: _retrySearch dialogId={dialogId} guid={guid} q={repr(fixedQuery)}", self._pluginRef)
            run_on_ui_thread(lambda: mdc.searchMessagesInChat(
                fixedQuery, dialogId, mergeDialogId or 0, guid, 0,
                replyMessageId or 0, user, chat, reaction
            ))
        except Exception as e:
            log(f"bettersearch [chat]: _retrySearch failed: {e}")
