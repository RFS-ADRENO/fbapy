from ..utils import DefaultFuncs, parse_and_check_login, EventEmitter, get_guid
from requests import Response
import json
import random
import paho.mqtt.client as mqtt
import time
from urllib.parse import urlparse

topics = [
    "/legacy_web",
    "/webrtc",
    "/rtc_multi",
    "/onevc",
    "/br_sr",  # Notification
    # Need to publish /br_sr right after this
    "/sr_res",
    "/t_ms",
    "/thread_typing",
    "/orca_typing_notifications",
    "/notify_disconnect",
    # Need to publish /messenger_sync_create_queue right after this
    "/orca_presence",
    # Will receive /sr_res right here.
    "/inbox",
    "/mercury",
    "/messaging_events",
    "/orca_message_notifications",
    "/pp",
    "/webrtc_response",
]


def listen_mqtt(default_funcs: DefaultFuncs, ctx: dict):
    form_get_seq_id = {
        "queries": '{"o0":{"doc_id":"3336396659757871","query_params":{"limit":1,"before":null,"tags":["INBOX"],"includeDeliveryReceipts":false,"includeSeqID":true}}}',
    }

    def connect_mqtt():
        print("Listening to MQTT...")
        message_emitter = EventEmitter()

        chat_on: bool = ctx["options"]["online"]
        foreground = False

        session_id = random.randint(1, 9007199254740991)
        user = {
            "u": ctx["user_id"],
            "s": session_id,
            "chat_on": chat_on,
            "fg": foreground,
            "d": get_guid(),
            "ct": "websocket",
            # App id from facebook
            "aid": 219994525426954,
            "mqtt_sid": "",
            "cp": 3,
            "ecp": 10,
            "st": topics,
            "pm": [],
            "dc": "",
            "no_auto_fg": True,
            "gas": None,
            "pack": [],
        }

        host = ""
        if ctx["mqtt_endpoint"]:
            host = f"{ctx['mqtt_endpoint']}&sid={session_id}"
        elif ctx["region"]:
            host = f"wss://edge-chat.facebook.com/chat?region={ctx['region'].lower()}&sid={session_id}"
        else:
            host = f"wss://edge-chat.facebook.com/chat?sid={session_id}"

        cookie_str = ""

        for cookie in default_funcs.session.cookies:
            cookie_str += cookie.name + "=" + cookie.value + "; "

        options = {
            "client_id": "mqttwsclient",
            "username": json.dumps(user, separators=(",", ":")),
            "clean": True,
            "ws_options": {
                "headers": {
                    "Cookie": cookie_str,
                    "Origin": "https://www.facebook.com",
                    "User-Agent": ctx["options"]["user_agent"],
                    "Referer": "https://www.facebook.com/",
                    "Host": "edge-chat.facebook.com",
                },
            },
            "keepalive": 10,
        }

        def on_connect(client: mqtt.Client, userdata, flags, rc):
            print("Connected with result code " + str(rc))

            topic = None

            queue = {
                "sync_api_version": 10,
                "max_deltas_able_to_process": 1000,
                "delta_batch_size": 500,
                "encoding": "JSON",
                "entity_fbid": ctx["user_id"],
            }

            if ctx["sync_token"]:
                topic = "/messenger_sync_get_diffs"
                queue["last_seq_id"] = ctx["last_seq_id"]
                queue["sync_token"] = ctx["sync_token"]
            else:
                topic = "/messenger_sync_create_queue"
                queue["initial_titan_sequence_id"] = ctx["last_seq_id"]
                queue["device_params"] = None

            client.publish(
                topic=topic,
                payload=json.dumps(queue, separators=(",", ":")),
                qos=1,
                retain=False,
            )

        def on_message(client, userdata, msg):
            print(msg.topic + " " + str(msg.payload))
            message_emitter.emit(msg.topic, msg.payload)

        def on_disconnect(client, userdata, rc):
            print("Disconnected with result code " + str(rc))

        def on_subscribe(client, userdata, mid, granted_qos):
            print("Subscribed: " + str(mid) + " " + str(granted_qos))

        def on_unsubscribe(client, userdata, mid):
            print("Unsubscribed: " + str(mid))

        def on_log(client, userdata, level, buf):
            print("Log: " + str(buf))

        c_mqtt = mqtt.Client(
            client_id=options["client_id"],
            clean_session=options["clean"],
            protocol=mqtt.MQTTv31,
            transport="websockets",
        )

        ctx["mqtt_client"] = c_mqtt

        c_mqtt.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
        # c_mqtt.enable_logger()

        c_mqtt.on_connect = on_connect
        c_mqtt.on_message = on_message
        c_mqtt.on_disconnect = on_disconnect
        c_mqtt.on_subscribe = on_subscribe
        c_mqtt.on_unsubscribe = on_unsubscribe
        # c_mqtt.on_log = on_log

        c_mqtt.username_pw_set(username=options["username"])

        parsed_host = urlparse(host)

        c_mqtt.ws_set_options(
            path=f"{parsed_host.path}?{parsed_host.query}",
            headers=options["ws_options"]["headers"],
        )

        # connect
        c_mqtt.connect(
            host=options["ws_options"]["headers"]["Host"],
            port=443,
            keepalive=options["keepalive"],
        )
        c_mqtt.loop_forever()

    def listen_mqtt():
        if ctx["first_listen"] is False:
            ctx["last_seq_id"] = None

        ctx["sync_token"] = None

        if ctx["first_listen"] is False or ctx["last_seq_id"] is None:
            get_seq_id()
        else:
            connect_mqtt()

        ctx["first_listen"] = False

    def get_seq_id():
        res: Response = default_funcs.post_with_defaults(
            "https://www.facebook.com/api/graphqlbatch/", form_get_seq_id
        )

        try:
            data = parse_and_check_login(res, ctx, default_funcs)

            if type(data) != list:
                raise Exception("Not logged in")
            else:
                last_data = data[len(data) - 1]

                if last_data["error_results"] > 0:
                    raise data[0].o0.errors

                if last_data["successful_results"] == 0:
                    raise Exception("getSeqId: there was no successful_results")

                try:
                    sync_sequence_id = data[0]["o0"]["data"]["viewer"][
                        "message_threads"
                    ]["sync_sequence_id"]

                    ctx["last_seq_id"] = sync_sequence_id
                    connect_mqtt()
                except:
                    raise Exception("getSeqId: no sync_sequence_id found.")
        except Exception as e:
            if "Not logged in" in str(e):
                ctx["logged_in"] = False

            raise e

    return listen_mqtt
