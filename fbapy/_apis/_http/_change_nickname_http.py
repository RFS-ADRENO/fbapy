from ..._utils import DefaultFuncs, parse_and_check_login


def change_nickname_http(default_funcs: DefaultFuncs, ctx: dict):
    def change(new_nickname: str, uid: str, thread_id: str):
        form = {
            "nickname": new_nickname,
            "participant_id": uid,
            "thread_or_other_fbid": thread_id,
        }

        res = default_funcs.post_with_defaults(
            "https://www.facebook.com/messaging/save_thread_nickname/?source=thread_settings&dpr=1",
            form,
            ctx,
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return change
