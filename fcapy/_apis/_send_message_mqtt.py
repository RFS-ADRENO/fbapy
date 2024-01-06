from .._utils import (
    DefaultFuncs,
    generate_offline_threading_id,
    is_callable,
    parse_and_check_login,
)
import time
import json
from paho.mqtt.client import Client
from requests import Response
from io import BufferedReader
from typing import Callable
from magic import Magic
import concurrent.futures

# @TODO: Add support for sending URL
def get_valid_mentions(text: str, mention: dict | list[dict]) -> list:
    if not isinstance(mention, dict) and not isinstance(mention, list):
        raise ValueError("Mentions must be a dict or list of dict")

    mentions = mention if isinstance(mention, list) else [mention]

    valid_mentions = []
    current_offset = 0
    for mention in mentions:
        if "id" in mention and "tag" in mention:
            provided_offset = mention.get("offset")
            tag_len = 0

            if type(provided_offset) is int:
                if provided_offset >= len(text):
                    break

                is_length_exceed = provided_offset + len(mention["tag"]) > len(text)
                tag_len = (
                    len(mention["tag"])
                    if not is_length_exceed
                    else len(text) - provided_offset
                )
                current_offset = provided_offset
            else:
                if current_offset >= len(text):
                    break

                find = text.find(mention["tag"], current_offset)
                if find != -1:
                    is_length_exceed = find + len(mention["tag"]) > len(text)
                    tag_len = (
                        len(mention["tag"])
                        if not is_length_exceed
                        else len(text) - find
                    )

                    current_offset = find

            valid_mentions.append(
                {
                    "i": mention["id"],
                    "o": current_offset,
                    "l": tag_len,
                }
            )

            current_offset += tag_len

    return valid_mentions


def send_message_mqtt(default_funcs: DefaultFuncs, ctx: dict):
    def make_send_task(task_payload: dict, thread_id: int):
        ctx["ws_task_number"] += 1
        task = {
            "failure_count": None,
            "label": "46",
            "payload": json.dumps(task_payload, separators=(",", ":")),
            "queue_name": str(thread_id),
            "task_id": ctx["ws_task_number"],
        }

        return task

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
            "https://www.facebook.com/ajax/mercury/upload.php",
            form_data["form"],
            files={
                "farr": form_data["attachment"]["farr"],
            },
        )

        res_data = parse_and_check_login(res, ctx, default_funcs)

        if "error" in res_data:
            raise res_data

        metadata = res_data["payload"]["metadata"]
        return isinstance(metadata, list) and metadata[0] or metadata.get("0")

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
                "attachment": {"farr": None},
            }

            if isinstance(attachment, BufferedReader):
                m = Magic(mime=True)
                mimetype = m.from_buffer(attachment.read())

                attachment.seek(0)

                form_data["attachment"]["farr"] = (
                    "file",
                    attachment,
                    mimetype,
                )
            else:
                form_data["attachment"]["farr"] = attachment

            forms.append(form_data)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(upload, forms)

        return results

    def handle_attachment(attachments: list) -> dict:
        uploaded_attachments = upload_attachment(attachments)

        attachments_ids = {
            "image_ids": [],
            "other_ids": [],
        }
        for file in uploaded_attachments:
            if file["filetype"] == "image/gif":
                attachments_ids["other_ids"].append(file["gif_id"])
            elif file["filetype"].startswith("image"):
                attachments_ids["image_ids"].append(file["fbid"])
            else:
                got_id = file.get("fbid") or file.get("gif_id") or file.get("audio_id") or file.get("video_id") or file.get("file_id")
                if got_id is not None:
                    attachments_ids["other_ids"].append(got_id)
                else:
                    print(f"Unknown file type: {json.dumps(file, indent=4)}")

        return attachments_ids

    def send(
        text: str,
        mention: dict | list[dict] | None = None,
        attachment: BufferedReader
        | tuple[str, BufferedReader, str]
        | list[BufferedReader | tuple[str, BufferedReader, str]]
        | None = None,
        thread_id: int = None,
        callback: Callable[[dict | None, dict | None], None] = None,
    ):
        if "mqtt_client" not in ctx:
            raise ValueError("Not connected to MQTT")

        mqtt: Client = ctx["mqtt_client"]

        if mqtt is None:
            raise ValueError("Not connected to MQTT")

        if thread_id is None:
            raise ValueError("thread_id is required")

        if text is None and attachment is None:
            raise ValueError("text or attachment required")

        text = str(text) if text is not None else ""

        ctx["ws_req_number"] += 1

        task_payload = {
            "initiating_source": 0,
            "multitab_env": 0,
            "otid": generate_offline_threading_id(),
            "send_type": 1,
            "skip_url_preview_gen": 0,
            # what is source for?
            "source": 0,
            "sync_group": 1,
            "text": text,
            "text_has_links": 0,
            "thread_id": int(thread_id),
        }

        if mention is not None and len(text) > 0:
            valid_mentions = get_valid_mentions(text, mention)

            task_payload["mention_data"] = {
                "mention_ids": ",".join([str(x["i"]) for x in valid_mentions]),
                "mention_lengths": ",".join([str(x["l"]) for x in valid_mentions]),
                "mention_offsets": ",".join([str(x["o"]) for x in valid_mentions]),
                "mention_types": ",".join(["p" for _ in valid_mentions]),
            }

        task = make_send_task(task_payload, thread_id)

        ctx["ws_task_number"] += 1
        task_mark_payload = {
            "last_read_watermark_ts": int(time.time() * 1000),
            "sync_group": 1,
            "thread_id": int(thread_id),
        }

        task_mark = {
            "failure_count": None,
            "label": "21",
            "payload": json.dumps(task_mark_payload, separators=(",", ":")),
            "queue_name": str(thread_id),
            "task_id": ctx["ws_task_number"],
        }

        content = {
            "app_id": "2220391788200892",
            "payload": {
                "data_trace_id": None,
                "epoch_id": int(generate_offline_threading_id()),
                "tasks": [],
                "version_id": "7545284305482586",
            },
            "request_id": ctx["ws_req_number"],
            "type": 3,
        }

        content["payload"]["tasks"].append(task)
        content["payload"]["tasks"].append(task_mark)

        if attachment is not None:
            attachments = attachment if isinstance(attachment, list) else [attachment]
            attachments_ids = handle_attachment(attachments)

            image_ids = attachments_ids["image_ids"]
            other_ids = attachments_ids["other_ids"]

            if len(image_ids) > 0:
                task_image_payload = {
                    "attachment_fbids": image_ids,
                    "otid": generate_offline_threading_id(),
                    "send_type": 3,
                    # what is source for?
                    "source": 0,
                    "sync_group": 1,
                    "text": None,
                    "thread_id": int(thread_id),
                }

                task_image = make_send_task(task_image_payload, thread_id)
                content["payload"]["tasks"].append(task_image)

            if len(other_ids) > 0:
                for other_id in other_ids:
                    task_other_payload = {
                        "attachment_fbids": [other_id],
                        "otid": generate_offline_threading_id(),
                        "send_type": 3,
                        # what is source for?
                        "source": 0,
                        "sync_group": 1,
                        "text": None,
                        "thread_id": int(thread_id),
                    }

                    task_other = make_send_task(task_other_payload, thread_id)
                    content["payload"]["tasks"].append(task_other)

        content["payload"] = json.dumps(content["payload"], separators=(",", ":"))

        if is_callable(callback):
            ctx["req_callbacks"][ctx["ws_req_number"]] = callback

        mqtt.publish(
            topic="/ls_req",
            payload=json.dumps(content, separators=(",", ":")),
            qos=1,
            retain=False,
        )

    return send
