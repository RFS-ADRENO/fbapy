from ..._utils import (
    DefaultFuncs,
    generate_offline_threading_id,
    generate_threading_id,
    generate_timestamp_relative,
    parse_and_check_login
)
from time import time


def add_user_to_group_http(default_funcs: DefaultFuncs, ctx: dict):
    def add(list_uid: list, thread_id: str):
        message_and_OTID = generate_offline_threading_id
        form = {
            "client": "mercury",
            "action_type": "ma-type:log-message",
            "author": "fbid:" + ctx["user_id"],
            "thread_id": "",
            "timestamp": int(round(time() * 1000)),
            "timestamp_absolute": "Today",
            "timestamp_relative": generate_timestamp_relative(),
            "timestamp_time_passed": "0",
            "is_unread": False,
            "is_cleared": False,
            "is_forward": False,
            "is_filtered_content": False,
            "is_filtered_content_bh": False,
            "is_filtered_content_account": False,
            "is_spoof_warning": False,
            "source": "source:chat:web",
            "source_tags[0]": "source:chat",
            "log_message_type": "log:subscribe",
            "status": "0",
            "offline_threading_id": message_and_OTID,
            "message_id": message_and_OTID,
            "threading_id": generate_threading_id(ctx["client_id"]),
            "manual_retry_cnt": "0",
            "thread_fbid": thread_id,
        }

        for id in range(len(list_uid)):
            form["log_message_data[added_participants][" + str(id) + "]"] = (
                "fbid:" + list_uid[id]
            )

        res = default_funcs.post_with_defaults(
            "https://www.facebook.com/messaging/send/", form, ctx
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return add
