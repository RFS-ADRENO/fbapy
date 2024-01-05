from ._utils import DefaultFuncs
from ._apis import *

class API:
    def __init__(self, default_funcs: DefaultFuncs, ctx: dict):
        ctx["api"] = self

        self.send_message = send_message(default_funcs, ctx)
        self.listen_mqtt = listen_mqtt(default_funcs, ctx)
        self.resolve_photo_url = resolve_photo_url(default_funcs, ctx)
        self.change_emoji  = change_emoji(default_funcs, ctx)
        self.unsend_message  = unsend_message(default_funcs, ctx)
        self.change_nickname  = change_nickname(default_funcs, ctx)
        self.read_status  = read_status(default_funcs, ctx)
        self.set_typing  = set_typing(default_funcs, ctx)
        self.create_new_group  = create_new_group(default_funcs, ctx)
        self.share_story  = share_story(default_funcs, ctx)
        self.set_pfp = set_pfp(default_funcs, ctx)
        self.send_message_mqtt = send_message_mqtt(default_funcs, ctx)
        self.remove_user_from_group = remove_user_from_group(default_funcs, ctx)
        self.add_user_to_group = add_user_to_group(default_funcs, ctx)
        self.change_bio = change_bio(default_funcs, ctx)
