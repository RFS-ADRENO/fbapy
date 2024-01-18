from ..._utils import (
    DefaultFuncs,
    generate_offline_threading_id,
    generate_timestamp_relative,
    generate_threading_id,
    get_signature_id,
    parse_and_check_login,
)
import time
from requests import Response
from io import BufferedReader
import concurrent.futures
from magic import Magic

allowed_keys = [
    "attachment",
    "url",
    "sticker",
    "emoji",
    "emojiSize",
    "body",
    "mentions",
    "location",
]


def send_message_http(default_funcs: DefaultFuncs, ctx: dict):
    def is_acceptable_attachment(attachment):
        return isinstance(attachment, BufferedReader) or (
            type(attachment) is tuple
            and len(attachment) == 3
            and (type(attachment[0]) is str and len(attachment[0]) > 0)
            and isinstance(attachment[1], BufferedReader)
            and type(attachment[2]) is str
        )

    def upload(form_data: dict):
        res: Response = default_funcs.post_form_data_with_default(
            "https://upload.facebook.com/ajax/mercury/upload.php",
            form_data["form"],
            files={
                "upload_1024": form_data["attachment"]["upload_1024"],
            },
        )

        res_data = parse_and_check_login(res, ctx, default_funcs)

        if "error" in res_data:
            raise res_data

        return res_data["payload"]["metadata"][0]

    def upload_attachment(attachments: list):
        forms = []

        for attachment in attachments:
            if not is_acceptable_attachment(attachment):
                raise ValueError(
                    {
                        "error": f"Attachment must be a BufferedReader or a tuple of (filename, BufferedReader, mimetype) not {type(attachment)}."
                    }
                )

            form_data = {
                "form": {"voice_clip": "true"},
                "attachment": {"upload_1024": None},
            }

            if isinstance(attachment, BufferedReader):
                m = Magic(mime=True)
                mimetype = m.from_buffer(attachment.read())

                attachment.seek(0)

                form_data["attachment"]["upload_1024"] = (
                    "file",
                    attachment,
                    mimetype,
                )
            else:
                form_data["attachment"]["upload_1024"] = attachment

            forms.append(form_data)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(upload, forms)

        return results

    def handle_location(msg: dict, form: dict):
        if "location" in msg and type(msg["location"]) is dict:
            latitude = msg["location"].get("latitude")
            longitude = msg["location"].get("longitude")

            if latitude is not None and longitude is not None:
                form["location_attachment[coordinates][latitude]"] = latitude
                form["location_attachment[coordinates][longitude]"] = longitude
                form["location_attachment[is_current_location]"] = bool(
                    msg["location"].get("current")
                )
            else:
                raise ValueError(
                    "Location must have latitude and longitude, not "
                    + str(msg["location"])
                )

    def handle_sticker(msg: dict, form: dict):
        if "sticker" in msg:
            form["sticker_id"] = msg["sticker"]

    def handle_attachment(msg: dict, form: dict):
        if "attachment" in msg:
            form["image_ids"] = []
            form["gif_ids"] = []
            form["file_ids"] = []
            form["video_ids"] = []
            form["audio_ids"] = []

            if type(msg["attachment"]) is not list:
                msg["attachment"] = [msg["attachment"]]

            files = upload_attachment(msg["attachment"])

            for file in files:
                if "image_id" in file:
                    form["image_ids"].append(file["image_id"])
                elif "gif_id" in file:
                    form["gif_ids"].append(file["gif_id"])
                elif "file_id" in file:
                    form["file_ids"].append(file["file_id"])
                elif "video_id" in file:
                    form["video_ids"].append(file["video_id"])
                elif "audio_id" in file:
                    form["audio_ids"].append(file["audio_id"])

    def handle_url(msg: dict, form: dict):
        pass

    def handle_emoji(msg: dict, form: dict):
        pass

    def handle_mention(msg: dict, form: dict):
        pass

    def send_content(form: dict, thread_id: str, is_group: bool):
        if is_group:
            form["thread_fbid"] = thread_id
        else:
            form["specific_to_list[0]"] = "fbid:" + thread_id
            form["specific_to_list[1]"] = "fbid:" + ctx["user_id"]
            form["other_user_fbid"] = thread_id

        res: Response = default_funcs.post_with_defaults(
            "https://www.facebook.com/messaging/send/", form
        )

        return parse_and_check_login(res, ctx, default_funcs)

    def send(
        msg: str | dict,
        thread_id: str,
        reply_to_message: str = None,
        is_group: bool = None,
    ):
        is_group = is_group if type(is_group) is bool else len(thread_id) > 15

        if not is_valid_msg(msg):
            raise ValueError("Message must be string or dict, not " + str(type(msg)))

        if type(msg) is str:
            msg = {"body": msg}

        disallowed_keys = [key for key in msg.keys() if key not in allowed_keys]

        if len(disallowed_keys) > 0:
            raise ValueError("Disallowed keys: " + str(disallowed_keys))

        message_and_otid = generate_offline_threading_id()

        form = {
            "client": "mercury",
            "action_type": "ma-type:user-generated-message",
            "author": "fbid:" + ctx["user_id"],
            "timestamp": int(time.time() * 1000),
            "timestamp_absolute": "Today",
            "timestamp_relative": generate_timestamp_relative(),
            "timestamp_time_passed": "0",
            "is_unread": False,
            "is_cleared": False,
            "is_forward": False,
            "is_filtered_content": False,
            "is_filtered_content_bh": False,
            "is_filtered_content_account": False,
            "is_filtered_content_quasar": False,
            "is_filtered_content_invalid_app": False,
            "is_spoof_warning": False,
            "source": "source:chat:web",
            "source_tags[0]": "source:chat",
            "body": msg["body"] if "body" in msg else "",
            "html_body": False,
            "ui_push_phase": "V3",
            "status": "0",
            "offline_threading_id": message_and_otid,
            "message_id": message_and_otid,
            "threading_id": generate_threading_id(ctx["client_id"]),
            "ephemeral_ttl_mode:": "0",
            "manual_retry_cnt": "0",
            "has_attachment": bool(
                msg.get("attachment") or msg.get("url") or msg.get("sticker")
            ),
            "signatureID": get_signature_id(),
            "replied_to_message_id": reply_to_message,
        }

        handle_location(msg, form)
        handle_sticker(msg, form)
        handle_attachment(msg, form)
        handle_url(msg, form)
        handle_emoji(msg, form)
        handle_mention(msg, form)

        return send_content(form, thread_id, is_group)

    return send


def is_valid_msg(msg):
    return type(msg) is dict or type(msg) is str
