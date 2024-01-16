import os
from os.path import join, dirname
from dotenv import load_dotenv

from fbapy import *

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

client = Client()

api = client.login(
    os.environ.get("APPSTATE"),
    options={
        "user_agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36"
    },
)

PREFIX = "?"


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def callback(event, api: API):
    try:
        if event is not None:
            if event["type"] == "message" or event["type"] == "message_reply":
                body: str = event["body"]  # guaranteed to exist
                print(f"Message: {body}")

                if body.startswith(PREFIX):
                    if body == PREFIX + "ping1":
                        api.send_message_mqtt("pong", event["thread_id"])
                    elif body == PREFIX + "ping2":
                        api.send_message(
                            "pong", event["thread_id"]
                        )
                    elif body == PREFIX + "hi":
                        api.send_message(
                            "hello", event["thread_id"], event["message_id"]
                        )
                    elif body == PREFIX + "meow":
                        api.send_message(
                            {"sticker": "554423694645485"},
                            event["thread_id"],
                            event["message_id"],
                        )
                    elif body == PREFIX + "where":
                        api.send_message(
                            {
                                "location": {
                                    "latitude": 10.764461306457537,
                                    "longitude": 106.66615124288597,
                                }
                            },
                            event["thread_id"],
                            event["message_id"],
                        )
                    elif body.startswith(PREFIX + "share ") and len(body) > 7:
                        args = body[7:].split("|")
                        story = args[0]
                        color = safe_cast(args[1] if len(args) >= 2 else None, int, 1)
                        font = safe_cast(args[2] if len(args) >= 3 else None, int, 1)

                        if color < 1 or color > len(CONSTS.LIST_COLORS):
                            api.send_message(
                                f"Invalid color index. Must be in range [0, {len(CONSTS.LIST_COLORS) - 1}]\nUse `{PREFIX}colors` to see all supported colors",
                                event["thread_id"],
                                event["message_id"],
                            )
                            return

                        if font < 1 or font > len(CONSTS.LIST_FONTS):
                            api.send_message(
                                f"Invalid font index. Must be in range [0, {len(CONSTS.LIST_FONTS_KEYS) - 1}]\nUse `{PREFIX}fonts` to see all supported fonts",
                                event["thread_id"],
                                event["message_id"],
                            )
                            return

                        color = CONSTS.LIST_COLORS[color - 1]
                        font = CONSTS.LIST_FONTS[font - 1]

                        api.share_story(story, preset_id=color, font_id=font)
                    elif body == PREFIX + "fonts":
                        api.send_message(
                            "All of these are supported fonts"
                            + "\n"
                            + "\n".join(
                                [
                                    f"{i+1}. {CONSTS.LIST_FONTS_KEYS[i]}"
                                    for i in range(len(CONSTS.LIST_FONTS_KEYS))
                                ]
                            ),
                            event["thread_id"],
                            event["message_id"],
                        )
                    elif body == PREFIX + "colors":
                        api.send_message(
                            {
                                "body": "All of these are supported presets",
                                "attachment": open(
                                    "assets/story_text_format_presets.png", "rb"
                                ),
                            },
                            event["thread_id"],
                            event["message_id"],
                        )
                    elif body == PREFIX + "imgs":
                        api.send_message(
                            {
                                "body": "All of these are supported presets",
                                "attachment": [
                                    open("assets/story_text_format_presets.png", "rb"),
                                    open("assets/a.jpg", "rb"),
                                    open("assets/a.jpg", "rb"),
                                ],
                            },
                            event["thread_id"],
                            event["message_id"],
                        )
                    else:
                        api.send_message(
                            "Unknown command", event["thread_id"], event["message_id"]
                        )

                if "attachments" in event and len(event["attachments"]) > 0:
                    pass
                    for attachment in event["attachments"]:
                        if (
                            "preview_url" not in attachment
                            or attachment["type"] == "video"
                        ):
                            print(
                                f"Attachment: {attachment['type']} - {attachment['url']}"
                            )
                        else:
                            print(
                                f"Attachment: {attachment['type']} - {attachment['preview_url']}"
                            )

                        if attachment["type"] == "sticker":
                            print("Sticker ID:", attachment["sticker_id"])
            else:
                print(event)
    except Exception as e:
        print(e)
        # print(event)


api.listen_mqtt(callback)
