from .._utils import DefaultFuncs, generate_offline_threading_id, is_callable
import json
from paho.mqtt.client import Client
from typing import Callable


def edit_message(default_funcs: DefaultFuncs, ctx: dict):
    def edit_message_mqtt(
        message_id: str,
        text: str,
        callback: Callable[[dict | None, dict | None], None] = None,
    ):
        if "mqtt_client" not in ctx:
            raise ValueError("Not connected to MQTT")

        mqtt: Client = ctx["mqtt_client"]

        if mqtt is None:
            raise ValueError("Not connected to MQTT")

        ctx["ws_req_number"] += 1

        ctx["ws_task_number"] += 1
        task_payload = {
            "message_id": message_id,
            "text": text,
        }

        task = {
            "failure_count": None,
            "label": "742",
            "payload": json.dumps(task_payload, separators=(",", ":")),
            "queue_name": "edit_message",
            "task_id": ctx["ws_task_number"],
        }

        content = {
            "app_id": "2220391788200892",
            "payload": {
                "data_trace_id": None,
                "epoch_id": int(generate_offline_threading_id()),
                "tasks": [],
                "version_id": "6903494529735864",
            },
            "request_id": ctx["ws_req_number"],
            "type": 3,
        }

        content["payload"]["tasks"].append(task)
        content["payload"] = json.dumps(content["payload"], separators=(",", ":"))

        if is_callable(callback):
            ctx["req_callbacks"][ctx["ws_req_number"]] = callback

        mqtt.publish(
            topic="/ls_req",
            payload=json.dumps(content, separators=(",", ":")),
            qos=1,
            retain=False,
        )

    return edit_message_mqtt
