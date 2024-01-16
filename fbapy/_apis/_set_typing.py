from .._utils import DefaultFuncs
import time
def set_typing(default_funcs: DefaultFuncs, ctx: dict):
        def typing(thread_id:str,status:bool):
            form = {
             "typ": "1" if status else "0",
            "thread": thread_id,
            "source": "mercury-chat",
            }
            default_funcs.post_with_defaults("https://www.facebook.com/ajax/messaging/typ.php",form,ctx)
        return typing