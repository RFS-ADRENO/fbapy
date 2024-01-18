from ..._utils import DefaultFuncs, parse_and_check_login
from requests import Response


def resolve_photo_url_http(default_funcs: DefaultFuncs, ctx: dict):
    def resolve_photo_url(photo_id: str):
        res: Response = default_funcs.get_with_defaults(
            "https://www.facebook.com/mercury/attachments/photo/",
            {"photo_id": photo_id},
        )

        res = parse_and_check_login(res, ctx, default_funcs)

        if type(res) is not dict:
            raise Exception("Not logged in")

        if "error" in res:
            raise Exception(res["error"])

        photo_url = res["jsmods"]["require"][0][3][0]

        return photo_url

    return resolve_photo_url
