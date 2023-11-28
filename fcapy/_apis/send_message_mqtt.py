from ..utils import DefaultFuncs, generate_offline_threading_id, generate_timestamp_relative, generate_threading_id, get_signature_id
import time
from requests import Response
import json
from paho.mqtt.client import Client

allowed_keys = ["attachment","url","sticker","emoji","emojiSize","body","mentions","location"]

ws_task_number = 1
ws_req_number = 1

def send_message_mqtt(default_funcs: DefaultFuncs, ctx: dict):
    def send(msg: str, thread_id: int):
        global ws_task_number
        global ws_req_number

        if "mqtt_client" not in ctx:
            raise ValueError("Not connected to MQTT")
        
        mqtt: Client = ctx["mqtt_client"]

        if mqtt is None:
            raise ValueError("Not connected to MQTT")
        
        ws_task_number += 1
        ws_req_number += 1

        task_payload = {
            # "initiating_source": 0,
            # "multitab_env": 0,
            "otid": generate_offline_threading_id(),
            "send_type": 1,
            # "skip_url_preview_gen": 0,
            "source": 0,
            # "sync_group": 1,
            "text": msg,
            # "text_has_links": 0,
            "thread_id": thread_id,
        }

        task = {
            "label": "46",
            "payload": json.dumps(task_payload, separators=(",", ":")),
            "queue_name": str(thread_id),
            "task_id": ws_task_number,
            "failure_count": None
        }

        content = {
            "request_id": ws_req_number,
            "type": 3,
            "payload": {
                "version_id": "3816854585040595",
                "tasks": [],
                "epoch_id": 6763184801413415579,
                "data_trace_id": None
            },
            "app_id": "772021112871879"
        }

        content["payload"]["tasks"].append(json.dumps(task, separators=(",", ":")))

        print(content)

        info = mqtt.publish(topic="/ls_req", payload=json.dumps(content, separators=(",", ":")), qos=1, retain=False)

        print(info)
    
    return send
