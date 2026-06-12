from android_utils import log
from . import loader
from ..dbg import dbg as _dbg

def teardown(plugin) -> None:
    lib = loader.getLib()
    if lib is not None:
        lib.freeIndex(plugin)
        loader._searchLib = None
        _dbg("bettersearch: library freed on unload", plugin)
