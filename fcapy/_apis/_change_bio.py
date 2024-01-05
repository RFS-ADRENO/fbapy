import json
from .._utils import DefaultFuncs


def change_bio(default_funcs: DefaultFuncs, ctx: dict):
    def change(bio_content: str, public_bio: bool):
        form = {
            "av": ctx["user_id"],
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "ProfileCometSetBioMutation",
            "doc_id": "6996613973732391",
            "variables": json.dumps(
                {"input": {
                    "attribution_id_v2": "ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,unexpected,1703941286245,183952,190055527696468,,;ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,unexpected,1703940792344,513946,190055527696468,,;ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,1703940775960,698443,190055527696468,,",
                    "bio": bio_content,
                    "publish_bio_feed_story": public_bio,
                    "actor_id": ctx["user_id"],
                    "client_mutation_id": "3"
                },
                    "hasProfileTileViewID": True,
                    "scale": 1.5,
                    "useDefaultActor": False
                }
            )
        }
        default_funcs.post_with_defaults(
            "https://www.facebook.com/api/graphql/", form, ctx).text
    return change
