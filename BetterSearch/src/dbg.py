from android_utils import log


def dbg(msg: str, plugin=None):
    # use this
    if plugin is not None and not plugin.get_setting("debug_logs", False):
        return
    log(msg)
