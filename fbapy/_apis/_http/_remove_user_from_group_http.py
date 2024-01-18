from ..._utils import DefaultFuncs, parse_and_check_login


def remove_user_from_group_http(default_funcs: DefaultFuncs, ctx: dict):
    def remove(uid: str, thread_id: str):
        form = {"uid": uid, "tid": thread_id}
        res = default_funcs.post_with_defaults(
            "https://www.facebook.com/chat/remove_participants", form, ctx
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return remove
