from .._utils import (
    DefaultFuncs,
    parse_and_check_login,
    get_guid,
    format_delta_message,
    decode_client_payload,
    _format_attachment,
)
from requests import Response
import json
import random
import paho.mqtt.client as mqtt
from urllib.parse import urlparse
from typing import Callable
import re


def parse_delta(default_funcs: DefaultFuncs, ctx: dict, delta: dict) -> dict:
    if "class" not in delta:
        return {"type": "unknown", "data": delta}

    def resolve_attachment_url(i: int):
        if "attachments" not in delta:
            return None  # I wonder if this will ever happen

        if len(delta["attachments"]) == i:
            formatted = format_delta_message(delta)

            if (
                ctx["options"]["self_listen"] is not True
                and formatted["sender_id"] == ctx["user_id"]
            ):
                return None

            return formatted

        elif (
            "mercury" in delta["attachments"][i]
            and delta["attachments"][i]["mercury"].get("attach_type") == "photo"
        ):
            try:
                res = ctx["api"].resolve_photo_url(delta["attachments"][i]["fbid"])
                delta["attachments"][i]["mercury"]["metadata"]["url"] = res
            except:
                pass

            return resolve_attachment_url(i + 1)
        else:
            return resolve_attachment_url(i + 1)

    listen_events = bool(ctx["options"]["listen_events"])

    if delta["class"] == "NewMessage":
        return resolve_attachment_url(0)
    elif delta["class"] == "ClientPayload":
        client_payload = decode_client_payload(delta["payload"])
        if "deltas" in client_payload:
            for delta in client_payload["deltas"]:
                if "deltaMessageReaction" in delta and listen_events:
                    return {
                        "type": "message_reaction",
                        "thread_id": str(
                            delta["deltaMessageReaction"]["threadKey"]["threadFbId"]
                            if "threadFbId"
                            in delta["deltaMessageReaction"]["threadKey"]
                            else delta["deltaMessageReaction"]["threadKey"][
                                "otherUserFbId"
                            ]
                        ),
                        "message_id": delta["deltaMessageReaction"]["messageId"],
                        "reaction": delta["deltaMessageReaction"].get("reaction"),
                        "sender_id": str(delta["deltaMessageReaction"]["senderId"]),
                        "user_id": str(delta["deltaMessageReaction"]["userId"]),
                    }
                elif "deltaRecallMessageData" in delta and listen_events:
                    return {
                        "type": "message_unsend",
                        "thread_id": str(
                            delta["deltaRecallMessageData"]["threadKey"]["threadFbId"]
                            if "threadFbId"
                            in delta["deltaRecallMessageData"]["threadKey"]
                            else delta["deltaRecallMessageData"]["threadKey"][
                                "otherUserFbId"
                            ]
                        ),
                        "message_id": delta["deltaRecallMessageData"]["messageID"],
                        "sender_id": str(delta["deltaRecallMessageData"]["senderID"]),
                        "deletion_timestamp": delta["deltaRecallMessageData"][
                            "deletionTimestamp"
                        ],
                        "timestamp": delta["deltaRecallMessageData"][
                            "messageTimestamp"
                        ],
                    }
                elif "deltaMessageReply" in delta:
                    m_data: list = (
                        json.loads(
                            delta["deltaMessageReply"]["message"]["data"]["prng"]
                        )
                        if "message" in delta["deltaMessageReply"]
                        and "data" in delta["deltaMessageReply"]["message"]
                        and "prng" in delta["deltaMessageReply"]["message"]["data"]
                        else []
                    )

                    body = delta["deltaMessageReply"]["message"].get("body") or ""

                    m_id = []
                    m_offset = []
                    m_length = []

                    for m in m_data:
                        m_id.append(m["i"])
                        m_offset.append(m["o"])
                        m_length.append(m["l"])

                    mentions = {}
                    for i in range(len(m_id)):
                        mentions[m_id[i]] = (body)[
                            m_offset[i] : m_offset[i] + m_length[i]
                        ]

                    attachments = []

                    if "attachments" in delta["deltaMessageReply"]["message"]:
                        for attachment in delta["deltaMessageReply"]["message"][
                            "attachments"
                        ]:
                            mercury = json.loads(attachment["mercuryJSON"])
                            attachment.update(mercury)

                            try:
                                formatted = _format_attachment(attachment)
                                attachments.append(formatted)
                            except Exception as e:
                                attachment["error"] = str(e)
                                attachment["type"] = "unknown"
                                attachments.append(attachment)

                    dict_to_return = {
                        "type": "message_reply",
                        "thread_id": str(
                            delta["deltaMessageReply"]["message"]["messageMetadata"][
                                "threadKey"
                            ]["threadFbId"]
                            if "threadFbId"
                            in delta["deltaMessageReply"]["message"]["messageMetadata"][
                                "threadKey"
                            ]
                            else delta["deltaMessageReply"]["message"][
                                "messageMetadata"
                            ]["threadKey"]["otherUserFbId"]
                        ),
                        "message_id": delta["deltaMessageReply"]["message"][
                            "messageMetadata"
                        ]["messageId"],
                        "sender_id": str(
                            delta["deltaMessageReply"]["message"]["messageMetadata"][
                                "actorFbId"
                            ]
                        ),
                        "attachments": attachments,
                        "args": re.split(r"\s+", body),
                        "body": body,
                        "mentions": mentions,
                        "timestamp": delta["deltaMessageReply"]["message"][
                            "messageMetadata"
                        ]["timestamp"],
                        "is_group": "threadFbId"
                        in delta["deltaMessageReply"]["message"]["messageMetadata"][
                            "threadKey"
                        ],
                        "participant_ids": [
                            str(u)
                            for u in delta["deltaMessageReply"]["message"][
                                "participants"
                            ]
                        ]
                        if "participants" in delta["deltaMessageReply"]["message"]
                        else None,
                    }

                    if "repliedToMessage" in delta["deltaMessageReply"]:
                        m_data = (
                            json.loads(
                                delta["deltaMessageReply"]["repliedToMessage"]["data"][
                                    "prng"
                                ]
                            )
                            if "data" in delta["deltaMessageReply"]["repliedToMessage"]
                            and "prng"
                            in delta["deltaMessageReply"]["repliedToMessage"]["data"]
                            else []
                        )

                        body = (
                            delta["deltaMessageReply"]["repliedToMessage"].get("body")
                            or ""
                        )

                        m_id = []
                        m_offset = []
                        m_length = []

                        for m in m_data:
                            m_id.append(m["i"])
                            m_offset.append(m["o"])
                            m_length.append(m["l"])

                        rmentions = {}

                        for i in range(len(m_id)):
                            rmentions[m_id[i]] = (body)[
                                m_offset[i] : m_offset[i] + m_length[i]
                            ]

                        attachments = []
                        if (
                            "attachments"
                            in delta["deltaMessageReply"]["repliedToMessage"]
                        ):
                            for attachment in delta["deltaMessageReply"][
                                "repliedToMessage"
                            ]["attachments"]:
                                mercury = json.loads(attachment["mercuryJSON"])
                                attachment.update(mercury)

                                try:
                                    formatted = _format_attachment(attachment)
                                    attachments.append(formatted)
                                except Exception as e:
                                    attachment["error"] = str(e)
                                    attachment["type"] = "unknown"
                                    attachments.append(attachment)

                        dict_to_return["message_reply"] = {
                            "thread_id": str(
                                delta["deltaMessageReply"]["repliedToMessage"][
                                    "messageMetadata"
                                ]["threadKey"]["threadFbId"]
                                if "threadFbId"
                                in delta["deltaMessageReply"]["repliedToMessage"][
                                    "messageMetadata"
                                ]["threadKey"]
                                else delta["deltaMessageReply"]["repliedToMessage"][
                                    "messageMetadata"
                                ]["threadKey"]["otherUserFbId"]
                            ),
                            "message_id": delta["deltaMessageReply"][
                                "repliedToMessage"
                            ]["messageMetadata"]["messageId"],
                            "sender_id": str(
                                delta["deltaMessageReply"]["repliedToMessage"][
                                    "messageMetadata"
                                ]["actorFbId"]
                            ),
                            "attachments": attachments,
                            "args": re.split(r"\s+", body),
                            "body": body,
                            "mentions": rmentions,
                            "timestamp": delta["deltaMessageReply"]["repliedToMessage"][
                                "messageMetadata"
                            ]["timestamp"],
                            "is_group": "threadFbId"
                            in delta["deltaMessageReply"]["repliedToMessage"][
                                "messageMetadata"
                            ]["threadKey"],
                            "participant_ids": [
                                str(u)
                                for u in delta["deltaMessageReply"]["repliedToMessage"][
                                    "participants"
                                ]
                            ]
                            if "participants"
                            in delta["deltaMessageReply"]["repliedToMessage"]
                            else None,
                        }
                    elif "replyToMessageId" in delta:
                        raise Exception(
                            "deltaMessageReply.replyToMessageId is not implemented yet."
                        )
                    else:
                        dict_to_return["delta"] = delta

                    if ctx["options"]["self_listen"] is not True:
                        if dict_to_return["sender_id"] == ctx["user_id"]:
                            return None

                    return dict_to_return

    pass


topics = [
    "/ls_resp",
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
            "aid": 5094267961737215,
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

            def dcn_timeout():
                client.disconnect()
                get_seq_id()

        def parse_mqtt_payload(payload: bytes | bytearray) -> dict:
            payload_str = payload.decode("utf-8")

            if payload_str[0] == "{":
                return json.loads(payload_str)
            else:
                return {"t": payload_str}

        def on_message(client, userdata, msg: mqtt.MQTTMessage):
            if msg.topic == "/t_ms":
                parsed = parse_mqtt_payload(msg.payload)

                if "firstDeltaSeqId" in parsed and "syncToken" in parsed:
                    ctx["last_seq_id"] = parsed["firstDeltaSeqId"]
                    ctx["sync_token"] = parsed["syncToken"]

                if "lastIssuedSeqId" in parsed:
                    ctx["last_seq_id"] = parsed["lastIssuedSeqId"]

                if "deltas" in parsed:
                    deltas: list = parsed["deltas"]

                    for delta in deltas:
                        parsed_delta = parse_delta(default_funcs, ctx, delta)
                        if parsed_delta is not None:
                            ctx["callback"](parsed_delta, ctx["api"])

            elif msg.topic == "/ls_resp":
                parsed = parse_mqtt_payload(msg.payload)

                print(parsed)

        def on_disconnect(client, userdata, rc):
            print("Disconnected with result code " + str(rc))

        def on_subscribe(client, userdata, mid, granted_qos):
            print("Subscribed: " + str(mid) + " " + str(granted_qos))

        def on_unsubscribe(client, userdata, mid):
            print("Unsubscribed: " + str(mid))

        c_mqtt = mqtt.Client(
            client_id=options["client_id"],
            clean_session=options["clean"],
            protocol=mqtt.MQTTv31,
            transport="websockets",
        )

        ctx["mqtt_client"] = c_mqtt

        c_mqtt.tls_set()
        c_mqtt.tls_insecure_set(True)

        c_mqtt.on_connect = on_connect
        c_mqtt.on_message = on_message
        c_mqtt.on_disconnect = on_disconnect
        c_mqtt.on_subscribe = on_subscribe
        c_mqtt.on_unsubscribe = on_unsubscribe

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

        try:
            c_mqtt.loop_forever()
        except KeyboardInterrupt:
            c_mqtt.disconnect()

    def listen_mqtt(callback: Callable):
        ctx["callback"] = callback

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
                raise Exception(
                    {
                        "error": "Not logged in",
                        "res": data,
                    }
                )
            else:
                last_data = data[len(data) - 1]

                if last_data["error_results"] > 0:
                    raise data[0].o0.errors

                if last_data["successful_results"] == 0:
                    raise Exception(
                        {
                            "error": "getSeqId: there was no successful_results",
                            "res": data,
                        }
                    )

                try:
                    sync_sequence_id = data[0]["o0"]["data"]["viewer"][
                        "message_threads"
                    ]["sync_sequence_id"]

                    ctx["last_seq_id"] = sync_sequence_id
                    connect_mqtt()
                except:
                    raise Exception(
                        {"error": "getSeqId: no sync_sequence_id found.", "res": data}
                    )
        except Exception as e:
            if (
                type(e.args[0]) == dict
                and "error" in e.args[0]
                and e.args[0]["error"] == "Not logged in"
            ):
                ctx["logged_in"] = False

            raise e

    return listen_mqtt
