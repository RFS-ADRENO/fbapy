from ..._utils import DefaultFuncs
import json


def get_user_info_http(default_funcs: DefaultFuncs, ctx: dict):
    def format_data(data):
        ret_obj = {}

        for prop, inner_obj in data.items():
            ret_obj[prop] = {
                "name": inner_obj["name"],
                "firstName": inner_obj["firstName"],
                "vanity": inner_obj["vanity"],
                "thumbSrc": inner_obj["thumbSrc"],
                "profileUrl": inner_obj["uri"],
                "gender": inner_obj["gender"],
                "type": inner_obj["type"],
                "isFriend": inner_obj["is_friend"],
            }

        return ret_obj

    def get_info(uid: str):
        form = {"ids[0]": uid}
        data = default_funcs.post_with_defaults(
            "https://www.facebook.com/chat/user_info/", form, ctx
        ).text
        return format_data(
            json.loads(data.replace("for (;;);", ""))["payload"]["profiles"]
        )

    return get_info
