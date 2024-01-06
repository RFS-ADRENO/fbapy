import random
import time
import base64
import json
from datetime import datetime
from requests import Session, Response
import re
from typing import Dict
from urllib.parse import urlparse, parse_qs
import inspect


def base64_decode(data: str) -> list:
    """
    Decode base64 data to dict

    :param data: base64 encoded data
    :return: dict
    """
    return json.loads(base64.b64decode(data.encode("utf-8")).decode("utf-8"))


def get_headers(
    url: str, options: dict = {}, ctx: dict = {}, customHeader: dict = {}
) -> dict:
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.facebook.com/",
        "Host": url.replace("https://", "").split("/")[0],
        "Origin": "https://www.facebook.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
        "Connection": "keep-alive",
    }

    if "user_agent" in options:
        headers["User-Agent"] = options["user_agent"]

    for key in customHeader:
        headers[key] = customHeader[key]

    if "region" in ctx:
        headers["X-MSGR-Region"] = ctx["region"]

    return headers


class DefaultFuncs:
    def __init__(self, session: Session, html: str, user_id: str, ctx: dict):
        self.req_counter = 1
        self.fbdtsg = get_from(html, 'name="fb_dtsg" value="', '"')

        self.ttstamp = "2"
        for i in range(0, len(self.ttstamp)):
            self.ttstamp += str(ord(self.ttstamp[i]))

        self.revision = get_from(html, 'revision":', ",")

        self.session = session
        self.user_id = user_id
        self.ctx = ctx

    def merge_with_defaults(self, old_dict: dict):
        new_dict = {
            "__user": self.user_id,
            "__req": base36encode(self.req_counter),
            "__rev": self.revision,
            "__a": 1,
            "fb_dtsg": self.fbdtsg
            if "fb_dtsg" not in self.ctx or self.ctx["fb_dtsg"] is None
            else self.ctx["fb_dtsg"],
            "jazoest": self.ttstamp
            if "ttstamp" not in self.ctx or self.ctx["ttstamp"] is None
            else self.ctx["ttstamp"],
        }

        self.req_counter += 1

        if old_dict is None:
            return new_dict

        for key in old_dict:
            if key not in new_dict:
                new_dict[key] = old_dict[key]

        return new_dict

    def get_with_defaults(self, url: str, qs: dict, ctxx: dict = {}):
        return self.session.get(
            url,
            params=self.merge_with_defaults(qs),
            headers=get_headers(url, ctx=ctxx),
            timeout=60,
        )

    def post_with_defaults(self, url: str, form: dict, ctxx: dict = {}):
        abc = self.merge_with_defaults(form)
        # print(json.dumps(abc, indent=4))
        return self.session.post(
            url,
            data=abc,
            headers=get_headers(url, ctx=ctxx),
            timeout=60,
        )

    def post_form_data_with_default(
        self, url: str, form: dict, qs: dict = {}, ctxx: dict = {}, files: dict = {}
    ):
        headers = get_headers(url, ctx=ctxx)
        del headers["Content-Type"]
        return self.session.post(
            url,
            data=self.merge_with_defaults(form),
            params=self.merge_with_defaults(qs),
            headers=headers,
            timeout=60,
            files=files,
        )


def base36encode(number: int, alphabet="0123456789abcdefghijklmnopqrstuvwxyz"):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError("number must be an integer")

    base36 = ""
    sign = ""

    if number < 0:
        sign = "-"
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def get_from(input_str, start_token, end_token):
    start = input_str.find(start_token) + len(start_token)
    if start < len(start_token):
        return ""

    last_half = input_str[start:]
    end = last_half.find(end_token)
    if end == -1:
        raise ValueError(f"Could not find endTime `{end_token}` in the given string.")

    return last_half[:end]


def generate_offline_threading_id() -> str:
    ret = int(time.time() * 1000)
    value = random.randint(0, 4294967295)
    binary_str = format(value, "022b")[-22:]
    msgs = bin(ret)[2:] + binary_str
    return str(int(msgs, 2))


def generate_timestamp_relative():
    d = datetime.now()
    return str(d.hour) + ":" + pad_zeros(str(d.minute))


def pad_zeros(value: str, len: int = 2):
    return value.zfill(len)


def generate_threading_id(client_id: str) -> str:
    k = int(time.time() * 1000)
    l = random.randint(0, 4294967295)
    m = client_id
    return f"<{k}:{l}-{m}@mail.projektitan.com>"


def get_signature_id():
    return format(random.randint(0, 2147483647), "x")


def parse_and_check_login(
    res: Response, ctx: dict, default_funcs: DefaultFuncs, retry_count: int = 0
) -> list | dict:
    if res.status_code >= 500 and res.status_code <= 600:
        if retry_count >= 5:
            raise Exception({
                "error": "Request retry failed. Check the `res` and `statusCode` property on this error.",
                "status_code": res.status_code,
                "res": res.text
            })

        retry_time = random.randint(0, 5000)

        print(
            f"Request failed with status code {res.status_code}. Retrying in {retry_time}ms..."
        )

        time.sleep(retry_time / 1000)

        url = res.request.url

        # check if its multipart/form-data

        if res.request.headers["Content-Type"] == "multipart/form-data":
            form = res.request.body
            res = default_funcs.post_form_data_with_default(url, form, {})
        else:
            form = res.request.body
            res = default_funcs.post_with_defaults(url, form)

        return parse_and_check_login(res, ctx, default_funcs, retry_count + 1)

    if res.status_code != 200:
        raise Exception(
            f"parseAndCheckLogin got status code: {res.status_code}. Bailing out of trying to parse response."
        )

    try:
        res: dict = json.loads(make_parsable(res.text))
        res = res.get("temp") or res
    except Exception as e:
        raise Exception({
            "error": "JSON.parse error. Check the `detail` property on this error.",
            "detail": e,
            "res": res.text
        })

    # In some cases the response contains only a redirect URL which should be followed
    if "redirect" in res and res["redirect"] and res["request"]["method"] == "GET":
        res = default_funcs.get_with_defaults(res["redirect"], {}, ctx)
        return parse_and_check_login(res, ctx, default_funcs)

    if (
        "jsmods" in res
        and "require" in res["jsmods"]
        and isinstance(res["jsmods"]["require"], list)
        and len(res["jsmods"]["require"]) > 0
        and isinstance(res["jsmods"]["require"][0], list)
        and len(res["jsmods"]["require"][0]) > 0
        and res["jsmods"]["require"][0][0] == "Cookie"
    ):
        res["jsmods"]["require"][0][3][0] = res["jsmods"]["require"][0][3][0].replace(
            "_js_", ""
        )
        cookie = format_cookie(res["jsmods"]["require"][0][3], "facebook")
        cookie2 = format_cookie(res["jsmods"]["require"][0][3], "messenger")

        default_funcs.session.cookies.set(
            cookie["name"],
            cookie["value"],
            path=cookie["path"],
            domain=cookie["domain"],
        )
        default_funcs.session.cookies.set(
            cookie2["name"],
            cookie2["value"],
            path=cookie2["path"],
            domain=cookie2["domain"],
        )

    # On every request we check if we got a DTSG and we mutate the context so that we use the latest
    # one for the next requests.
    if (
        "jsmods" in res
        and isinstance(res["jsmods"], dict)
        and "require" in res["jsmods"]
        and isinstance(res["jsmods"]["require"], list)
    ):
        arr = res["jsmods"]["require"]
        for i in range(0, len(arr)):
            if arr[i][0] == "DTSG" and arr[i][1] == "setToken":
                ctx["fb_dtsg"] = arr[i][3][0]

                # Update ttstamp since that depends on fb_dtsg
                ctx["ttstamp"] = "2"
                for j in range(0, len(ctx["fb_dtsg"])):
                    ctx["ttstamp"] += str(ord(ctx["fb_dtsg"][j]))

    if "error" in res and res["error"] == 1357001:
        raise Exception({
            "error": "Not logged in."
        })

    return res


def make_parsable(html) -> str:
    without_for_loop = re.sub(r"for\s*\(\s*;\s*;\s*\)\s*;\s*", "", html)

    # Handling multiple JSON objects in the same response
    maybe_multiple_objects = re.split(r"\}\r\n *\{", without_for_loop)
    if len(maybe_multiple_objects) == 1:
        return maybe_multiple_objects[0]

    return '{"temp":[' + "},{".join(maybe_multiple_objects) + "]}"


def format_cookie(arr: list, url: str) -> dict:
    return {"name": arr[0], "value": arr[1], "path": arr[3], "domain": url + ".com"}


class EventEmitter:
    def __init__(self):
        self._callbacks: Dict[str, callable] = {}

    def on(self, event_name, function):
        self._callbacks[event_name] = self._callbacks.get(event_name, []) + [function]
        return function

    def emit(self, event_name, *args, **kwargs):
        [function(*args, **kwargs) for function in self._callbacks.get(event_name, [])]

    def off(self, event_name, function):
        self._callbacks.get(event_name, []).remove(function)


def get_guid():
    section_length = int(time.time() * 1000)
    guid_template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"

    def generate_random_char(c):
        nonlocal section_length
        r = int((section_length + random.random() * 16) % 16)
        section_length = int(section_length / 16)
        return (
            format(r, "x")
            if c == "x"
            else format((r & 0x3) | 0x8, "x")
            if c == "y"
            else c
        )

    guid = "".join(generate_random_char(c) if c != "-" else "-" for c in guid_template)
    return guid


def format_delta_message(delta: dict):
    meta_data = delta["messageMetadata"]

    mdata = []

    if "data" in delta and "prng" in delta["data"]:
        mdata = json.loads(delta["data"]["prng"])

    m_id = []
    m_offset = []
    m_length = []
    mentions = {}
    body = (delta["body"] if "body" in delta else "").strip()
    args = re.split(r"\s+", body) if body != "" else []

    for i in range(0, len(mdata)):
        m_id.append(mdata[i]["i"])
        m_offset.append(mdata[i]["o"])
        m_length.append(mdata[i]["l"])

    for i in range(0, len(m_id)):
        mentions[m_id[i]] = body[m_offset[i] : m_offset[i] + m_length[i]]

    attachments = []
    if "attachments" in delta:
        for attachment in delta["attachments"]:
            attachments.append(_format_attachment(attachment))

    return {
        "type": "message",
        "sender_id": format_id(str(meta_data["actorFbId"])),
        "thread_id": format_id(
            str(
                meta_data["threadKey"]["threadFbId"]
                if "threadFbId" in meta_data["threadKey"]
                else meta_data["threadKey"]["otherUserFbId"]
            )
        ),
        "args": args,
        "body": body,
        "message_id": meta_data["messageId"],
        "attachments": attachments,
        "mentions": mentions,
        "timestamp": meta_data["timestamp"],
        "is_group": "threadFbId" in meta_data["threadKey"],
        "participant_ids": meta_data["participants"]
        if "participants" in meta_data
        else [],
    }


def format_id(id: str):
    return id if id is None else re.sub(r"(fb)?id[:.]", "", id)


def _format_attachment(
    attachment_one: dict, attachment_two: dict = {"id": "", "image_data": {}}
) -> dict:
    attachment_one = (
        "mercury" in attachment_one and attachment_one["mercury"] or attachment_one
    )

    blob = (
        attachment_one["blob_attachment"] if "blob_attachment" in attachment_one else {}
    )
    _type = (
        "__typename" in blob
        and blob["__typename"]
        or "attach_type" in blob
        and blob["attach_type"]
        or None
    )

    if _type is None and "sticker_attachment" in attachment_one:
        _type = "StickerAttachment"
        blob = attachment_one["sticker_attachment"]
    elif _type is None and "extensible_attachment" in attachment_one:
        if (
            "story_attachment" in attachment_one["extensible_attachment"]
            and attachment_one["extensible_attachment"]["story_attachment"].get("target") is not None
            and attachment_one["extensible_attachment"]["story_attachment"]["target"].get("__typename") == "MessageLocation"
        ):
            _type = "MessageLocation"
        else:
            _type = "ExtensibleAttachment"

        blob = attachment_one["extensible_attachment"]

    if _type == "sticker":
        return {
            "type": "sticker",
            "id": str(attachment_one["metadata"]["stickerID"]),
            "url": attachment_one["url"],
            "pack_id": str(attachment_one["metadata"]["packID"]),
            "sprite_url": attachment_one["metadata"]["spriteURI"],
            "sprite_url_2x": attachment_one["metadata"]["spriteURI2x"],
            "width": attachment_one["metadata"]["width"],
            "height": attachment_one["metadata"]["height"],
            "caption": attachment_two["caption"],
            "description": attachment_two["description"],
            "frame_count": attachment_one["metadata"]["frameCount"],
            "frame_rate": attachment_one["metadata"]["frameRate"],
            "frames_per_row": attachment_one["metadata"]["framesPerRow"],
            "frames_per_col": attachment_one["metadata"]["framesPerCol"],
            "sticker_id": str(attachment_one["metadata"]["stickerID"]),
            "sprite_uri": attachment_one["metadata"]["spriteURI"],
            "sprite_uri_2x": attachment_one["metadata"]["spriteURI2x"],
        }
    elif _type == "file":
        return {
            "type": "file",
            "filename": attachment_one["name"],
            "id": str(attachment_two["id"]),
            "url": attachment_one["url"],
            "is_malicious": attachment_two["is_malicious"],
            "content_type": attachment_two["mime_type"],
            "name": attachment_one["name"],
            "mime_type": attachment_two["mime_type"],
            "file_size": attachment_two["file_size"],
        }
    elif _type == "photo":
        return {
            "type": "photo",
            "id": str(attachment_one["metadata"]["fbid"]),
            "filename": attachment_one["fileName"],
            "thumbnail_url": attachment_one["thumbnail_url"],
            "preview_url": attachment_one["preview_url"],
            "preview_width": attachment_one["preview_width"],
            "preview_height": attachment_one["preview_height"],
            "large_preview_url": attachment_one["large_preview_url"],
            "large_preview_width": attachment_one["large_preview_width"],
            "large_preview_height": attachment_one["large_preview_height"],
            "url": attachment_one["metadata"]["url"],
            "width": attachment_one["metadata"]["dimensions"].split(",")[0],
            "height": attachment_one["metadata"]["dimensions"].split(",")[1],
            "name": attachment_one["fileName"],
        }
    elif _type == "animated_image":
        return {
            "type": "animated_image",
            "id": str(attachment_two["id"]),
            "filename": attachment_two["filename"],
            "preview_url": attachment_one["preview_url"],
            "preview_width": attachment_one["preview_width"],
            "preview_height": attachment_one["preview_height"],
            "url": attachment_two["image_data"]["url"],
            "width": attachment_two["image_data"]["width"],
            "height": attachment_two["image_data"]["height"],
            "name": attachment_one["name"],
            "facebook_url": attachment_one["url"],
            "thumbnail_url": attachment_one["thumbnail_url"],
            "mime_type": attachment_two["mime_type"],
            "raw_gif_image": attachment_two["image_data"]["raw_gif_image"],
            "raw_webp_image": attachment_two["image_data"]["raw_webp_image"],
            "animated_gif_url": attachment_two["image_data"]["animated_gif_url"],
            "animated_gif_preview_url": attachment_two["image_data"][
                "animated_gif_preview_url"
            ],
            "animated_webp_url": attachment_two["image_data"]["animated_webp_url"],
            "animated_webp_preview_url": attachment_two["image_data"][
                "animated_webp_preview_url"
            ],
        }
    elif _type == "share":
        return {
            "type": "share",
            "id": str(attachment_one["share"]["share_id"]),
            "url": attachment_two["href"],
            "title": attachment_one["share"]["title"],
            "description": attachment_one["share"]["description"],
            "source": attachment_one["share"]["source"],
            "image": attachment_one["share"]["media"]["image"],
            "width": attachment_one["share"]["media"]["image_size"]["width"],
            "height": attachment_one["share"]["media"]["image_size"]["height"],
            "playable": attachment_one["share"]["media"]["playable"],
            "duration": attachment_one["share"]["media"]["duration"],
            "subattachments": attachment_one["share"]["subattachments"],
            "properties": {},
            "animated_image_size": attachment_one["share"]["media"][
                "animated_image_size"
            ],
            "facebook_url": attachment_one["share"]["uri"],
            "target": attachment_one["share"]["target"],
            "style_list": attachment_one["share"]["style_list"],
        }
    elif _type == "video":
        return {
            "type": "video",
            "id": str(attachment_one["metadata"]["fbid"]),
            "filename": attachment_one["name"],
            "preview_url": attachment_one["preview_url"],
            "preview_width": attachment_one["preview_width"],
            "preview_height": attachment_one["preview_height"],
            "url": attachment_one["url"],
            "width": attachment_one["metadata"]["dimensions"].split(",")[0],
            "height": attachment_one["metadata"]["dimensions"].split(",")[1],
            "duration": attachment_one["metadata"]["duration"],
            "video_type": "unknown",
            "thumbnail_url": attachment_one["thumbnail_url"],
        }
    elif _type == "MessageImage":
        return {
            "type": "photo",
            "id": str(blob["legacy_attachment_id"]),
            "filename": blob["filename"],
            "thumbnail_url": blob["thumbnail"]["uri"],
            "preview_url": blob["preview"]["uri"],
            "preview_width": blob["preview"]["width"],
            "preview_height": blob["preview"]["height"],
            "large_preview_url": blob["large_preview"]["uri"],
            "large_preview_width": blob["large_preview"]["width"],
            "large_preview_height": blob["large_preview"]["height"],
            "url": blob["large_preview"]["uri"],
            "width": blob["original_dimensions"]["x"],
            "height": blob["original_dimensions"]["y"],
            "name": blob["filename"],
        }
    elif _type == "MessageAnimatedImage":
        return {
            "type": "animated_image",
            "id": str(blob["legacy_attachment_id"]),
            "filename": blob["filename"],
            "preview_url": blob["preview_image"]["uri"],
            "preview_width": blob["preview_image"]["width"],
            "preview_height": blob["preview_image"]["height"],
            "url": blob["animated_image"]["uri"],
            "width": blob["animated_image"]["width"],
            "height": blob["animated_image"]["height"],
            "thumbnail_url": blob["preview_image"]["uri"],
            "name": blob["filename"],
            "facebook_url": blob["animated_image"]["uri"],
            "raw_gif_image": blob["animated_image"]["uri"],
            "animated_gif_url": blob["animated_image"]["uri"],
            "animated_gif_preview_url": blob["preview_image"]["uri"],
            "animated_webp_url": blob["animated_image"]["uri"],
            "animated_webp_preview_url": blob["preview_image"]["uri"],
        }
    elif _type == "MessageVideo":
        return {
            "type": "video",
            "id": str(blob["legacy_attachment_id"]),
            "filename": blob["filename"],
            "preview_url": blob["large_image"]["uri"],
            "preview_width": blob["large_image"]["width"],
            "preview_height": blob["large_image"]["height"],
            "url": blob["playable_url"],
            "width": blob["original_dimensions"]["x"],
            "height": blob["original_dimensions"]["y"],
            "duration": blob["playable_duration_in_ms"],
            "video_type": blob["video_type"].lower(),
            "thumbnail_url": blob["large_image"]["uri"],
        }
    elif _type == "MessageAudio":
        return {
            "type": "audio",
            "id": str(blob.get("legacy_attachment_id")),
            "filename": blob["filename"],
            "audio_type": blob["audio_type"],
            "duration": blob["playable_duration_in_ms"],
            "url": blob["playable_url"],
            "is_voicemail": blob["is_voicemail"],
        }
    elif _type == "StickerAttachment":
        return {
            "type": "sticker",
            "id": str(blob["id"]),
            "url": blob["url"],
            "pack_id": (blob.get("pack") or {}).get("id"),
            "sprite_url": blob["sprite_image"],
            "sprite_url_2x": blob["sprite_image_2x"],
            "width": blob["width"],
            "height": blob["height"],
            "caption": blob["label"],
            "description": blob["label"],
            "frame_count": blob["frame_count"],
            "frame_rate": blob["frame_rate"],
            "frames_per_row": blob["frames_per_row"],
            "frames_per_col": blob["frames_per_column"],
            "sticker_id": blob["id"],
            "sprite_uri": blob["sprite_image"],
            "sprite_uri_2x": blob["sprite_image_2x"],
        }
    elif _type == "MessageLocation":
        url_attach = blob["story_attachment"].get("url")
        media_attach = blob["story_attachment"].get("media")

        u = parse_qs(urlparse(url_attach).query).get("u")[0]
        where1 = parse_qs(urlparse(u).query).get("where1")[0]
        address = where1.split(", ")

        latitude = None
        longitude = None

        try:
            latitude = float(address[0])
            longitude = float(address[1])
        except:
            pass

        image_url = None
        width = None
        height = None

        if media_attach and "image" in media_attach:
            image_url = media_attach["image"]["uri"]
            width = media_attach["image"]["width"]
            height = media_attach["image"]["height"]

        return {
            "type": "location",
            "id": blob["legacy_attachment_id"],
            "latitude": latitude,
            "longitude": longitude,
            "image": image_url,
            "width": width,
            "height": height,
            "url": u or url_attach,
            "address": where1,
            "facebook_url": blob["story_attachment"]["url"],
            "target": blob["story_attachment"]["target"],
            "style_list": blob["story_attachment"]["style_list"],
        }
    elif _type == "ExtensibleAttachment":
        properties = {}

        for cur in blob["story_attachment"]["properties"]:
            properties[cur["key"]] = cur["value"]["text"]
            
        story_attm = blob["story_attachment"]
        media = blob["story_attachment"].get("media") or {}

        media_image = media.get("image") or {}

        return {
            "type": "share",
            "id": blob["legacy_attachment_id"],
            "url": story_attm.get("url"),
            "title": story_attm["title_with_entities"].get("text"),
            "description": (story_attm.get("description") or {}).get("text"),
            "soure": (story_attm.get("source") or {}).get("text"),
            "image": media_image.get("uri"),
            "width": media_image.get("width"),
            "height": media_image.get("height"),
            "playable": media.get("is_playable"),
            "duration": media.get("playable_duration_in_ms"),
            "playable_url": media.get("playable_url"),
            "subattachments": story_attm.get("subattachments"),
            "properties": properties,
            "facebook_url": story_attm.get("url"),
            "target": story_attm.get("target"),
            "style_list": story_attm.get("style_list"),
        }
    elif _type == "MessageFile":
        return {
            "type": "file",
            "filename": blob["filename"],
            "id": blob["message_file_fbid"],
            "url": blob["url"],
            "is_malicious": blob["is_malicious"],
            "content_type": blob["content_type"],
            "name": blob["filename"],
            "mime_type": "",
            "file_size": -1,
        }
    elif _type == "error":
        return {
            "type": "error",
            "attachment_one": attachment_one,
            "attachment_two": attachment_two,
        }
    else:
        return {
            "type": "unknown",
            "_type": _type,
            "attachment_one": attachment_one,
            "attachment_two": attachment_two,
        }


def decode_client_payload(payload):
    def utf8_array_to_str(array):
        out = ""
        i = 0
        length = len(array)

        while i < length:
            c = array[i]
            i += 1
            if (
                c >> 4 == 0
                or c >> 4 == 1
                or c >> 4 == 2
                or c >> 4 == 3
                or c >> 4 == 4
                or c >> 4 == 5
                or c >> 4 == 6
                or c >> 4 == 7
            ):
                out += chr(c)
            elif c >> 4 == 12 or c >> 4 == 13:
                char2 = array[i]
                i += 1
                out += chr(((c & 0x1F) << 6) | (char2 & 0x3F))
            elif c >> 4 == 14:
                char2 = array[i]
                i += 1
                char3 = array[i]
                i += 1
                out += chr(
                    ((c & 0x0F) << 12) | ((char2 & 0x3F) << 6) | ((char3 & 0x3F) << 0)
                )

        return out

    return json.loads(utf8_array_to_str(payload))


def format_delta_read_receipt(delta: dict):
    return {
        "reader": str(delta["threadKey"].get("otherUserFbId") or delta.get("actorFbId")),
        "time": delta["actionTimestampMs"],
        "threadID": format_id(
            str(delta["threadKey"].get("otherUserFbId") or delta["threadKey"].get("threadFbId"))
        ),
        "type": "read_receipt"
    }

def get_admin_text_message_type(type: str):
    if type == "change_thread_theme":
        return "log:thread-color"
    elif type == "change_thread_quick_reaction": # deprecated ?
        return "log:thread-icon"
    elif type == "change_thread_nickname":
        return "log:user-nickname"
    elif type == "change_thread_admins":
        return "log:thread-admins"
    elif type == "group_poll":
        return "log:thread-poll"
    elif type == "change_thread_approval_mode":
        return "log:thread-approval-mode"
    elif type == "messenger_call_log" or type == "participant_joined_group_call":
        return "log:thread-call"
    else:
        return type


def format_delta_event(delta: dict):
    log_message_type = None
    log_message_data = None

    if delta["class"] == "AdminTextMessage":
        log_message_type = get_admin_text_message_type(delta["type"])
        log_message_data = delta.get("untypedData")
    elif delta["class"] == "ThreadName":
        log_message_type = "log:thread-name"
        log_message_data = {"name": delta.get("name")}
    elif delta["class"] == "ParticipantsAddedToGroupThread":
        log_message_type = "log:subscribe"
        log_message_data = {"addedParticipants": delta.get("addedParticipants")}
    elif delta["class"] == "ParticipantLeftGroupThread":
        log_message_type = "log:unsubscribe"
        log_message_data = {"leftParticipantFbId": delta.get("leftParticipantFbId")}

    return {
        "type": "event",
        "thread_id": format_id(
            str(
                delta["messageMetadata"]["threadKey"].get("threadFbId")
                or delta["messageMetadata"]["threadKey"].get("otherUserFbId")
            )
        ),
        "logMessageType": log_message_type,
        "logMessageData": log_message_data,
        "logMessageBody": delta["messageMetadata"].get("adminText"),
        "author": delta["messageMetadata"].get("actorFbId"),
        "participantIDs": delta.get("participants") or [],
    }

def is_edit_message_resp(payload: dict):
    try:
        return payload["step"][1][2][2][1][1] == "editMessage"
    except:
        return False

def get_mid_and_tid_from_resp_payload(payload: dict):
    try:
        if is_edit_message_resp(payload):
            return {
                "mid": payload["step"][1][2][2][1][2],
                "tid": None
            }
        return {
            "mid": payload["step"][1][2][2][1][3],
            "tid": payload["step"][4][2][2][1][2][1]
        }
    except:
        return None
    
def get_error_message_from_resp_payload(payload: dict):
    try:
        return payload["step"][3][2][2][1][1]
    except:
        return "Unknown error"

def is_callable(func: callable) -> bool:
    try:
        inspect.signature(func)
        return True
    except:
        return False
