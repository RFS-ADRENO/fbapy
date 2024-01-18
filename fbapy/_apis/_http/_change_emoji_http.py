from ..._utils import DefaultFuncs, parse_and_check_login


def change_emoji_http(default_funcs: DefaultFuncs, ctx: dict):
    def change(emoji: str, thread_id: str):
        form = {}
        form["emoji_choice"] = emoji
        form["thread_or_other_fbid"] = thread_id
        
        res = default_funcs.post_with_defaults(
            "https://www.facebook.com/messaging/save_thread_emoji/?source=thread_settings&__pc=EXP1%3Amessengerdotcom_pkg",
            form,
            ctx,
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return change
