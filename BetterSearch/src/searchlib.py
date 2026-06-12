import ctypes
import json
import threading
from android_utils import log

def _dbg(msg: str, plugin=None):
    log(msg)

def isRussian(text: str) -> bool:
    for ch in text:
        if '\u0400' <= ch <= '\u04FF':
            return True
    return False

# keyboard layout map
_RU_TO_LAT = {
    0x0439: 'q', 0x0446: 'w', 0x0443: 'e', 0x043A: 'r', 0x0435: 't',
    0x043D: 'y', 0x0433: 'u', 0x0448: 'i', 0x0449: 'o', 0x0437: 'p',
    0x0444: 'a', 0x044B: 's', 0x0432: 'd', 0x0430: 'f', 0x043F: 'g',
    0x0440: 'h', 0x043E: 'j', 0x043B: 'k', 0x0434: 'l', 0x0436: ';',
    0x044D: "'", 0x044F: 'z', 0x0447: 'x', 0x0441: 'c', 0x043C: 'v',
    0x0438: 'b', 0x0442: 'n', 0x044C: 'm', 0x0431: ',', 0x044E: '.',
}

_VOWELS = set('aeiouy')

def fixLayout(text: str) -> str:
    result = []
    for c in text.lower():
        result.append(_RU_TO_LAT.get(ord(c), c))
    return ''.join(result)

def looksLikeWrongLayout(query: str) -> bool:
    if not isRussian(query):
        return False
    fixed = fixLayout(query)
    alpha = [c for c in fixed if c != ' ']
    if not alpha:
        return False
    if not all(c.isalpha() for c in alpha):
        return False
    vowels = sum(1 for c in alpha if c in _VOWELS)
    return (vowels / len(alpha)) >= 0.2


class SearchLib:
    def __init__(self, path: str):
        self._lib = ctypes.CDLL(path)
        self._lib.search_build_index.restype = ctypes.c_int
        self._lib.search_build_index.argtypes = [ctypes.c_char_p]
        self._lib.search_query.restype = ctypes.c_void_p
        self._lib.search_query.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        self._lib.search_free_index.restype = None
        self._lib.search_free_index.argtypes = [ctypes.c_int]
        self._lib.search_free_str.restype = None
        self._lib.search_free_str.argtypes = [ctypes.c_void_p]
        self._lib.msg_score.restype = ctypes.c_float
        self._lib.msg_score.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.dialog_score.restype = ctypes.c_float
        self._lib.dialog_score.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._handle = -1
        self._lock = threading.Lock()

    def buildIndex(self, pluginsJson: str, plugin=None):
        with self._lock:
            if self._handle >= 0:
                self._lib.search_free_index(self._handle)
            self._handle = self._lib.search_build_index(pluginsJson.encode("utf-8"))
            _dbg(f"bettersearch: index built, handle={self._handle}", plugin)

    def query(self, q: str, isRussianQuery: bool, plugin=None) -> list:
        with self._lock:
            if self._handle < 0:
                _dbg("bettersearch: query called but handle is invalid, skipping", plugin)
                return []
            ptr = self._lib.search_query(
                self._handle,
                q.encode("utf-8"),
                1 if isRussianQuery else 0,
                1
            )
            if not ptr:
                _dbg(f"bettersearch: search_query returned NULL for q={repr(q)}", plugin)
                return []
            try:
                result = json.loads(ctypes.string_at(ptr).decode("utf-8"))
            finally:
                self._lib.search_free_str(ptr)
            _dbg(f"bettersearch: query q={repr(q)} isRussian={isRussianQuery} -> {len(result)} results: {result}", plugin)
            return result

    def freeIndex(self, plugin=None):
        with self._lock:
            if self._handle >= 0:
                self._lib.search_free_index(self._handle)
                _dbg(f"bettersearch: index freed, handle was {self._handle}", plugin)
                self._handle = -1

    def msgScore(self, text: str, query: str) -> float:
        try:
            return float(self._lib.msg_score(
                text.encode("utf-8"),
                query.encode("utf-8")
            ))
        except Exception as e:
            _dbg(f"bettersearch: msg_score failed: {e}")
            return 0.0

    def dialogScore(self, name: str, username: str, about: str, query: str) -> float:
        try:
            return float(self._lib.dialog_score(
                (name     or "").encode("utf-8"),
                (username or "").encode("utf-8"),
                (about    or "").encode("utf-8"),
                query.encode("utf-8")
            ))
        except Exception as e:
            _dbg(f"bettersearch: dialog_score failed: {e}")
            return 0.0
