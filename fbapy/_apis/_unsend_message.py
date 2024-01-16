from .._utils import DefaultFuncs
def unsend_message(default_funcs: DefaultFuncs, ctx: dict):
		def unsend(message_id:str):
			form={
			"message_id": message_id
            }
			default_funcs.post_with_defaults("https://www.facebook.com/messaging/unsend_message/",form,ctx)
		return unsend