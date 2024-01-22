from .._utils import (
    DefaultFuncs,
    parse_and_check_login,
    get_guid,
    format_delta_message,
    decode_client_payload,
    _format_attachment,
    format_delta_read_receipt,
    format_delta_event,
    format_id,
    get_mid_and_tid_from_resp_payload,
    get_error_message_from_resp_payload,
)
from requests import Response
import json
import random
import paho.mqtt.client as mqtt
from urllib.parse import urlparse
from typing import Callable
import re
import inspect
import ssl


def parse_delta(default_funcs: DefaultFuncs, ctx: dict, delta: dict) -> dict:
    if "class" not in delta:
        return {"type": "unknown", "data": json.dumps(delta, indent=4)}

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
                res = ctx["api"].http.resolve_photo_url(delta["attachments"][i]["fbid"])
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
                elif "deltaUpdateThreadEmoji" in delta and listen_events:
                    return {
                        "type": "event",
                        "thread_id": str(
                            delta["deltaUpdateThreadEmoji"]["threadKey"].get(
                                "threadFbId"
                            )
                            or delta["deltaUpdateThreadEmoji"]["threadKey"].get(
                                "otherUserFbId"
                            )
                        ),
                        "log_message_type": "log:thread-icon",
                        "log_message_data": {
                            "emoji": delta["deltaUpdateThreadEmoji"]["emoji"]
                        },
                        "timestamp": None,
                        "author": None,
                        "participant_ids": [],
                    }
                elif "deltaUpdatePinnedMessagesV2" in delta and listen_events:
                    return {
                        "type": "event",
                        "thread_id": str(
                            delta["deltaUpdatePinnedMessagesV2"]["threadKey"].get(
                                "threadFbId"
                            )
                            or delta["deltaUpdatePinnedMessagesV2"]["threadKey"].get(
                                "otherUserFbId"
                            )
                        ),
                        "log_message_type": "log:thread-pinned-message",
                        "log_message_data": {
                            "newPinnedMessages": delta["deltaUpdatePinnedMessagesV2"][
                                "newPinnedMessages"
                            ],
                            "removedPinnedMessages": delta[
                                "deltaUpdatePinnedMessagesV2"
                            ]["removedPinnedMessages"],
                        },
                        "timestamp": None,
                        "author": None,
                        "participant_ids": [],
                    }

    # This is because the loop in the ClientPayload changes the delta, will refactor later.
    # for now, just return None if the delta doesn't have a class key
    if delta.get("class") is None:
        print("Unknown delta: " + json.dumps(delta, indent=4))
        return None
    if delta["class"] != "NewMessage" and ctx["options"]["listen_events"] != True:
        return None

    if delta["class"] == "ReadReceipt":
        fmt_msg = None

        try:
            fmt_msg = format_delta_read_receipt(delta)
        except e:
            raise Exception(
                {
                    "error": "Failed to format read receipt",
                    "detail": e,
                    "res": delta,
                    "type": "parse_error",
                }
            )

        if ctx["options"]["self_listen"] is not True:
            if fmt_msg["reader"] == ctx["user_id"]:
                return None

        return fmt_msg
    elif delta["class"] == "AdminTextMessage":
        if (
            delta["type"] == "change_thread_theme"
            or delta["type"] == "change_thread_nickname"
            or delta["type"] == "change_thread_admins"
            or delta["type"] == "change_thread_approval_mode"
            or delta["type"] == "group_poll"
            or delta["type"] == "messenger_call_log"
            or delta["type"] == "participant_joined_group_call"
        ):
            fmt_msg = None
            try:
                fmt_msg = format_delta_event(delta)
            except e:
                raise Exception(
                    {
                        "error": "Failed to format admin message",
                        "detail": e,
                        "res": delta,
                        "type": "parse_error",
                    }
                )

            if ctx["options"]["self_listen"] is not True:
                if fmt_msg.get("author") == ctx["user_id"]:
                    return None

            return fmt_msg
        else:
            return None
    elif (
        delta["class"] == "ThreadName"
        or delta["class"] == "ParticipantsAddedToGroupThread"
        or delta["class"] == "ParticipantLeftGroupThread"
    ):
        fmt_msg = None
        try:
            fmt_msg = format_delta_event(delta)
        except e:
            raise Exception(
                {
                    "error": "Failed to format admin message",
                    "detail": e,
                    "res": delta,
                    "type": "parse_error",
                }
            )

        if ctx["options"]["self_listen"] is not True:
            if fmt_msg.get("author") == ctx["user_id"]:
                return None

        return fmt_msg
    elif delta["class"] == "ForcedFetch":
        if delta.get("threadKey") is None:
            return None

        mid = delta.get("messageId")
        tid = delta["threadKey"].get("threadFbId")

        if mid and tid:
            form = {
                "av": None,
                "queries": json.dumps(
                    {
                        "o0": {
                            # This doc_id is valid as of March 25, 2020
                            "doc_id": "2848441488556444",
                            "query_params": {
                                "thread_and_message_id": {
                                    "thread_id": str(tid),
                                    "message_id": mid,
                                },
                            },
                        }
                    }
                ),
            }

            res = default_funcs.post_with_defaults(
                "https://www.facebook.com/api/graphqlbatch/", form=form
            )
            res_data = parse_and_check_login(res, ctx, default_funcs)

            if res_data[len(res_data) - 1].get("error_results") > 0:
                raise res_data[0].o0.errors

            if res_data[len(res_data) - 1].get("successful_results") == 0:
                raise Exception(
                    {
                        "error": "forcedFetch: there was no successful_results",
                        "res": res_data,
                    }
                )

            fetch_data = res_data[0]["o0"]["data"]["message"]

            if type(fetch_data) != dict:
                raise Exception(f"forcedFetch: fetch_data is not a dict: {fetch_data}")
            else:
                __typename = fetch_data.get("__typename")
                if __typename == "ThreadImageMessage":
                    if ctx["options"]["self_listen"] is not True:
                        if fetch_data["message_sender"]["id"] == ctx["user_id"]:
                            return None

                    has_metadata = "image_with_metadata" in fetch_data

                    return {
                        "type": "event",
                        "thread_id": format_id(str(tid)),
                        "log_message_type": "log:thread-image",
                        "log_message_data": {
                            "image": {
                                "attachment_id": fetch_data["image_with_metadata"][
                                    "legacy_attachment_id"
                                ]
                                if has_metadata
                                else None,
                                "width": fetch_data["image_with_metadata"][
                                    "original_dimensions"
                                ]["x"]
                                if has_metadata
                                else None,
                                "height": fetch_data["image_with_metadata"][
                                    "original_dimensions"
                                ]["y"]
                                if has_metadata
                                else None,
                                "url": fetch_data["image_with_metadata"]["preview"][
                                    "uri"
                                ]
                                if has_metadata
                                else None,
                            }
                        },
                        "log_message_body": fetch_data.get("snippet"),
                        "timestamp": fetch_data.get("timestamp_precise"),
                        "author": fetch_data["message_sender"].get("id"),
                        "participant_ids": []
                    }
                elif __typename == "UserMessage":
                    return {
                        "type": "message",
                        "sender_id": fetch_data["message_sender"]["id"],
                        "body": fetch_data["message"].get("text") or "",
                        "thread_id": format_id(str(tid)),
                        "message_id": fetch_data["message_id"],
                        "attachments": [
                            {
                                "type": "share",
                                "id": fetch_data["extensible_attachment"].get(
                                    "legacy_attachment_id"
                                ),
                                "url": fetch_data["extensible_attachment"][
                                    "story_attachment"
                                ].get("url"),
                                "title": fetch_data["extensible_attachment"][
                                    "story_attachment"
                                ]
                                .get("title_with_entities")
                                .get("text"),
                                "description": fetch_data["extensible_attachment"][
                                    "story_attachment"
                                ]["description"].get("text"),
                                "source": fetch_data["extensible_attachment"][
                                    "story_attachment"
                                ].get("source"),
                                "image": (
                                    (
                                        fetch_data["extensible_attachment"][
                                            "story_attachment"
                                        ].get("media")
                                        or {}
                                    ).get("image")
                                    or {}
                                ).get("uri"),
                                "width": (
                                    (
                                        fetch_data["extensible_attachment"][
                                            "story_attachment"
                                        ].get("media")
                                        or {}
                                    ).get("image")
                                    or {}
                                ).get("width"),
                                "height": (
                                    (
                                        fetch_data["extensible_attachment"][
                                            "story_attachment"
                                        ].get("media")
                                        or {}
                                    ).get("image")
                                    or {}
                                ).get("height"),
                                "playable": (
                                    fetch_data["extensible_attachment"][
                                        "story_attachment"
                                    ].get("media")
                                    or {}
                                ).get("playable_duration_in_ms")
                                or 0,
                                "subattachments": fetch_data[
                                    "extensible_attachment"
                                ].get("subattachments"),
                                "properties": fetch_data["extensible_attachment"][
                                    "story_attachment"
                                ].get("properties"),
                            }
                        ],
                        "mentions": {},
                        "timestamp": int(fetch_data["timestamp_precise"]),
                        "is_group": fetch_data["message_sender"]["id"] != str(tid),
                    }

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
            "a": ctx["options"]["user_agent"],
            "u": ctx["user_id"],
            "s": session_id,
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
            host = f"{ctx['mqtt_endpoint']}&sid={session_id}&cid={get_guid()}"
        elif ctx["region"]:
            host = f"wss://edge-chat.facebook.com/chat?region={ctx['region'].lower()}&sid={session_id}&cid={get_guid()}"
        else:
            host = (
                f"wss://edge-chat.facebook.com/chat?sid={session_id}&cid={get_guid()}"
            )

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

            for topic in topics:
                client.subscribe(topic, qos=1)

            client.publish(
                topic="/ls_app_settings",
                payload=json.dumps(
                    {"ls_fdid": "", "ls_sv": "6928813347213944"},
                    separators=(",", ":"),
                ),
                qos=1,
                retain=False,
            )

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

        def parse_mqtt_payload(payload: bytes | bytearray) -> dict:
            payload_str = payload.decode("utf-8")

            if payload_str[0] == "{":
                return json.loads(payload_str)
            else:
                return {"t": payload_str}

        def on_message(client, userdata, msg: mqtt.MQTTMessage):
            parsed = parse_mqtt_payload(msg.payload)
            if msg.topic == "/t_ms":
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

            elif (
                msg.topic == "/thread_typing"
                or msg.topic == "/orca_typing_notifications"
            ):
                ctx["callback"](
                    {
                        "type": "typ",
                        "isTyping": bool(parsed["state"]),
                        "from": str(parsed["sender_fbid"]),
                        "thread_id": format_id(
                            str(parsed.get("thread") or parsed.get("sender_fbid"))
                        ),
                    },
                    ctx["api"],
                )
            elif msg.topic == "/orca_presence":
                if not ctx["options"]["update_presence"]:
                    for data in parsed["list"]:
                        l=None
                        if data.get("l"):
                            l=int(data["l"]) * 1000
                        ctx["callback"](
                            {
                                "type": "presence",
                                "user_id": str(data["u"]),
                                "timestamp": l,
                                "status": data["p"],
                            },
                            ctx["api"],
                        )

            elif msg.topic == "/ls_resp":
                print("Received message from topic " + msg.topic)
                parsed = parse_mqtt_payload(msg.payload)

                if "payload" in parsed:
                    payload = json.loads(parsed["payload"])
                    mid_tid = get_mid_and_tid_from_resp_payload(payload)

                    req_cb = ctx["req_callbacks"].get(parsed["request_id"])

                    if req_cb is not None:
                        params = inspect.signature(req_cb).parameters
                        if mid_tid is not None:
                            if len(params) == 2:
                                req_cb(
                                    {
                                        "message_id": mid_tid.get("mid"),
                                        "thread_id": mid_tid.get("tid")
                                    },
                                    None
                                )
                            elif len(params) == 1:
                                req_cb({
                                    "message_id": mid_tid.get("mid"),
                                    "thread_id": mid_tid.get("tid")
                                })
                            elif len(params) == 0:
                                req_cb()
                        else:
                            error_msg = get_error_message_from_resp_payload(payload)
                            if len(params) == 2:
                                req_cb(None, error_msg)
                            elif len(params) == 1:
                                req_cb(None)
                            elif len(params) == 0:
                                req_cb()

                        del ctx["req_callbacks"][parsed["request_id"]]
                else:
                    print("No payload in response: " + json.dumps(parsed, indent=4))

            else:
                print("Received message from topic " + msg.topic)
                pass

        def on_disconnect(client, userdata, rc):
            print("Disconnected with result code " + str(rc))

            if rc == mqtt.MQTT_ERR_CONN_REFUSED:
                client.disconnect()

        c_mqtt = mqtt.Client(
            client_id=options["client_id"],
            clean_session=options["clean"],
            protocol=mqtt.MQTTv31,
            transport="websockets",
        )

        ctx["mqtt_client"] = c_mqtt

        c_mqtt.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
        c_mqtt.tls_insecure_set(True)

        c_mqtt.on_connect = on_connect
        c_mqtt.on_message = on_message
        c_mqtt.on_disconnect = on_disconnect

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
