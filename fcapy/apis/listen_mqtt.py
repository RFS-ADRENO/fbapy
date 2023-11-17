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

    def listen_mqtt():
        message_emitter = EventEmitter()

        if ctx["first_listen"] is False:
            ctx["last_seq_id"] = None

        ctx["sync_token"] = None
        ctx["t_mqtt_called"] = True


        if ctx["first_listen"] == False or ctx["last_seq_id"] is None:
            get_seq_id()

        chat_on: bool = ctx["options"]["online"]
        foreground = False

        session_id = random.randint(0, 9007199254740991)
        user = {
            "u": ctx["user_id"],
            "S": session_id,
            "chat_on": chat_on,
            "fg": foreground,
            "d": get_guid(),
            "ct": "websocket",
            # App id from facebook
            "aid": "219994525426954",
            "mqtt_sid": "",
            "cp": 3,
            "ecp": 10,
            "st": [],
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
            "clientId": "mqttwsclient",
            "protocolId": "MQIsdp",
            "protocolVersion": 3,
            "username": json.dumps(user),
            "clean": True,
            "wsOptions": {
                "headers": {
                    "Cookie": cookie_str,
                    "Origin": "https://www.facebook.com",
                    "User-Agent": ctx["options"]["user_agent"],
                    "Referer": "https://www.facebook.com/",
                    "Host": "edge-chat.facebook.com",
                },
                "origin": "https://www.facebook.com",
                "protocolVersion": 13,
            },
            "keepalive": 10,
            "reschedulePings": False,
        }

        ctx["mqtt_client"] = mqtt.Client(
            client_id=options["clientId"],
            clean_session=options["clean"],
            protocol=mqtt.MQTTv311,
            transport="websockets",
        )

        ctx["mqtt_client"].enable_logger()

        def on_connect(client, userdata, flags, rc):
            print("Connected with result code " + str(rc))
            client.subscribe([(topic, 0) for topic in topics])

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

        ctx["mqtt_client"].on_connect = on_connect
        ctx["mqtt_client"].on_message = on_message
        ctx["mqtt_client"].on_disconnect = on_disconnect
        ctx["mqtt_client"].on_subscribe = on_subscribe
        ctx["mqtt_client"].on_unsubscribe = on_unsubscribe
        ctx["mqtt_client"].on_log = on_log

        ctx["mqtt_client"].tls_set()
        print(json.dumps(user, indent=4))
        ctx["mqtt_client"].username_pw_set(username=json.dumps(user, separators=(",", ":")))

        parsed_host = urlparse(host)

        ctx["mqtt_client"].ws_set_options(
            path= f"{parsed_host.path}?{parsed_host.query}",
            headers=options["wsOptions"]["headers"],
        )
        
        # connect
        ctx["mqtt_client"].connect(
            host=options["wsOptions"]["headers"]["Host"],
            port=443,
            keepalive=options["keepalive"],
        )
        ctx["mqtt_client"].loop_forever()

    def get_seq_id():
        ctx["t_mqtt_called"] = False
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
                    listen_mqtt()
                except:
                    raise Exception("getSeqId: no sync_sequence_id found.")
        except Exception as e:
            if "Not logged in" in str(e):
                ctx["logged_in"] = False

            raise e

    return listen_mqtt
