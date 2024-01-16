from .._utils import DefaultFuncs
def remove_user_from_group(default_funcs: DefaultFuncs, ctx: dict):
		def remove(uid:str,thread_id:str):
			form= {
                "uid": uid,
                "tid": thread_id
                }
			default_funcs.post_with_defaults("https://www.facebook.com/chat/remove_participants",form,ctx)
		return remove