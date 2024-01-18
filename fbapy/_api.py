from ._utils import DefaultFuncs
from ._apis import *

class GRAPHQLAPI:
    def __init__(self, default_funcs: DefaultFuncs, ctx: dict):
        self.create_new_group = graphql.create_new_group_graphql(default_funcs, ctx)
        self.share_story = graphql.share_story_graphql(default_funcs, ctx)
        self.set_profile_picture = graphql.set_pfp_graphql(default_funcs, ctx)
        self.change_bio = graphql.change_bio_graphql(default_funcs, ctx)

class HTTPAPI:
    def __init__(self, default_funcs: DefaultFuncs, ctx: dict):
        self.send_message = http.send_message_http(default_funcs, ctx)
        self.change_emoji = http.change_emoji_http(default_funcs, ctx)
        self.unsend_message = http.unsend_message_http(default_funcs, ctx)
        self.add_user_to_group = http.add_user_to_group_http(default_funcs, ctx)
        self.change_nickname = http.change_nickname_http(default_funcs, ctx)

        self.read_status = http.read_status_http(default_funcs, ctx)
        self.set_typing = http.set_typing_http(default_funcs, ctx)
        
        self.remove_user_from_group = http.remove_user_from_group_http(default_funcs, ctx)
        self.get_user_info = http.get_user_info_http(default_funcs, ctx)

        self.resolve_photo_url = http.resolve_photo_url_http(default_funcs, ctx)

class API:
    def __init__(self, default_funcs: DefaultFuncs, ctx: dict):
        ctx["api"] = self

        self.listen_mqtt = listen_mqtt(default_funcs, ctx)

        self.send_message = send_message(default_funcs, ctx)
        self.send_sticker = send_sticker(default_funcs, ctx)
        self.edit_message = edit_message(default_funcs, ctx)

        self.graphql = GRAPHQLAPI(default_funcs, ctx)
        self.http = HTTPAPI(default_funcs, ctx)
    