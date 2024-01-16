from .._utils import DefaultFuncs
import time
def read_status(default_funcs: DefaultFuncs, ctx: dict):
        def read(thread_id:str,status:bool):
            form = {
            "watermarkTimestamp": int(time.time() * 1000),
            "shouldSendReadReceipt": "true",
            "ids[{}]".format(thread_id) : "true" if status else "false"
            }
            default_funcs.post_with_defaults("https://www.facebook.com/ajax/mercury/change_read_status.php",form,ctx)
        return read