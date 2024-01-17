from .._utils import DefaultFuncs, generate_offline_threading_id, is_callable
import time
import json
from paho.mqtt.client import Client
from typing import Callable


def send_sticker(default_funcs: DefaultFuncs, ctx: dict):
    def add_reply_metadata(task_payload: dict, message_id: str):
        if message_id is not None:
            if type(message_id) is not str:
                raise ValueError("message_id must be a string")

            task_payload["reply_metadata"] = {
                "reply_source_id": message_id,
                "reply_source_type": 1,
                "reply_type": 0,
            }

    def send(
        sticker_id: int,
        thread_id: str,
        message_id: str = None,
        callback: Callable[[dict | None, dict | None], None] = None,
    ):
        if "mqtt_client" not in ctx:
            raise ValueError("Not connected to MQTT")

        mqtt: Client = ctx["mqtt_client"]

        if mqtt is None:
            raise ValueError("Not connected to MQTT")

        if thread_id is None:
            raise ValueError("thread_id is required")

        ctx["ws_req_number"] += 1

        ctx["ws_task_number"] += 1
        task_payload = {
            "initiating_source": 0,
            "multitab_env": 0,
            "otid": generate_offline_threading_id(),
            "send_type": 2,
            "skip_url_preview_gen": 0,
            # what is source for?
            "source": 0,
            "sticker_id": int(sticker_id),
            "sync_group": 1,
            "text_has_links": 0,
            "thread_id": int(thread_id),
        }

        add_reply_metadata(task_payload, message_id)

        task = {
            "failure_count": None,
            "label": "46",
            "payload": json.dumps(task_payload, separators=(",", ":")),
            "queue_name": str(thread_id),
            "task_id": ctx["ws_task_number"],
        }

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
