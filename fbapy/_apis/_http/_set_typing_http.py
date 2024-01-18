from ..._utils import DefaultFuncs, parse_and_check_login


def set_typing_http(default_funcs: DefaultFuncs, ctx: dict):
    def typing(thread_id: str, status: bool):
        form = {
            "typ": "1" if status else "0",
            "thread": thread_id,
            "source": "mercury-chat",
        }
        res = default_funcs.post_with_defaults(
            "https://www.facebook.com/ajax/messaging/typ.php", form, ctx
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return typing
