from .._utils import DefaultFuncs, parse_and_check_login
import json
import requests
from io import BufferedReader
from typing import Tuple


def set_pfp(default_funcs: DefaultFuncs, ctx: dict):
    def upload(avatar: Tuple[str, BufferedReader, str]):
        form = {}

        res = default_funcs.post_form_data_with_default(
            "https://www.facebook.com/profile/picture/upload",
            form=form,
            qs={
                "av": ctx["user_id"],
                "profile_id": ctx["user_id"],
                "photo_source": "57",
            },
            files={"file": avatar},
        )

        return parse_and_check_login(res, ctx, default_funcs)


    def set_pfp_graph(avatar: Tuple[str, BufferedReader, str]):
        up = upload(avatar)
        if "error" in up:
            raise up
        
        id = up["payload"]["fbid"]

        form = {
            "av": ctx["user_id"],
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "ProfileCometProfilePictureSetMutation",
            "variables": json.dumps(
                {
                    "input": {
                        "attribution_id_v2": "ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,unexpected,1702523833067,512584,190055527696468,,;CometHomeRoot.react,comet.home,via_cold_start,1702523826865,789289,4748854339,,",
                        "caption": "",
                        "existing_photo_id": id,
                        "expiration_time": None,
                        "profile_id": ctx["user_id"],
                        "profile_pic_method": "EXISTING",
                        "profile_pic_source": "TIMELINE",
                        "scaled_crop_rect": {
                            "height": 1,
                            "width": 0.625,
                            "x": 0.10833,
                            "y": 0,
                        },
                        "skip_cropping": True,
                        "actor_id": ctx["user_id"],
                        "client_mutation_id": "1",
                    },
                    "isPage": False,
                    "isProfile": True,
                    "sectionToken": "UNKNOWN",
                    "collectionToken": "UNKNOWN",
                    "scale": 2,
                }
            ),
            "doc_id": "7105779189485678",
        }
        res: requests.Response = default_funcs.post_with_defaults(
            "https://www.facebook.com/api/graphql/", form, ctx
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return set_pfp_graph
