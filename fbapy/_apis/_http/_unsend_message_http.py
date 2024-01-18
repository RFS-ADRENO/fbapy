from ..._utils import DefaultFuncs, parse_and_check_login


def unsend_message_http(default_funcs: DefaultFuncs, ctx: dict):
    def unsend(message_id: str):
        form = {"message_id": message_id}
        res = default_funcs.post_with_defaults(
            "https://www.facebook.com/messaging/unsend_message/", form, ctx
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return unsend
