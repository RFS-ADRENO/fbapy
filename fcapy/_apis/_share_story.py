from .._utils import DefaultFuncs, parse_and_check_login
import random
import json
import requests

# https://github.com/RFS-ADRENO/fcapy/blob/main/assets/story_text_format_presets.png
# The list below follows the order of the image above (from left to right, top to bottom)
PRESET_IDS = [
    "401372137331149",
    "276148839666236",
    "2163607613910521",
    "525779004528357",
    "1009318275928628",
    "452508575242041",
    "277332376527537",
    "241165263466288",

    "459530701251156",
    "2173297922999264",
    "367314917184744",
    "316152702351373",
    "1793841914061298",
    "2349018378676171",
    "236995927208996",
    "554617635055752",

    "410811529670314",
    "2013736355407001",
    "1858565907563681",
    "474022893007699",
    "464786114026686",
    "236819723594098",
    "314741219075524",
    "456542378188554",

    "338912070167253",
    "768161006877937",
    "856609964679094",
    "1187607261408676",
    "299352527433933",
    "280807115950091",
]

FONT_IDS = [
    "233490655168261", # Simple
    "1191814831024887", # Clean
    "516266749248495", # Casual
    "2133975226905828", # Fancy
    "1919119914775364", # Headline
]

def share_story(default_funcs: DefaultFuncs, ctx: dict):
    def share_story_graphql(story: str, preset_id: str = "401372137331149", font_id: str = "233490655168261"):

        if preset_id not in PRESET_IDS:
            raise ValueError("Invalid preset_id")
        
        if font_id not in FONT_IDS:
            raise ValueError("Invalid font_id")

        form = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "StoriesCreateMutation",
            "doc_id": "6197602830367217",
            "variables": json.dumps(
                {
                    "input": {
                        "audiences": [
                            {
                                "stories": {
                                    "self": {"target_id": ctx["user_id"]},
                                }
                            }
                        ],
                        "audiences_is_complete": True,
                        "source": "WWW",
                        "message": {"ranges": [], "text": story},
                        "text_format_metadata": {
                            "inspirations_custom_font_id": font_id,
                        },
                        "text_format_preset_id": preset_id,
                        "tracking": [None],
                        "actor_id": ctx["user_id"],
                        "client_mutation_id": str(random.randint(0, 1024)),
                    },
                }
            ),
            "av": ctx["user_id"],
        }
        res: requests.Response = default_funcs.post_with_defaults(
            "https://www.facebook.com/api/graphql/", form, ctx
        )

        return parse_and_check_login(res, ctx, default_funcs)

    return share_story_graphql
