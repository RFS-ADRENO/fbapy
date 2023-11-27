import random
import time
import base64
import json
from datetime import datetime
from requests import Session, Response
import re
from typing import Dict
from urllib.parse import urlparse, parse_qs


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
        return self.session.post(
            url,
            data=self.merge_with_defaults(form),
            headers=get_headers(url, ctx=ctxx),
            timeout=60,
        )

    def post_form_data_with_default(
        self, url: str, form: dict, qs: dict, ctxx: dict = {}
    ):
        return self.session.post(
            url,
            data=self.merge_with_defaults(form),
            params=self.merge_with_defaults(qs),
            headers=get_headers(url, ctx=ctxx),
            timeout=60,
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
):
    if res.status_code >= 500 and res.status_code <= 600:
        if retry_count >= 5:
            raise Exception("Request retry limit exceeded")

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

    data = None
    try:
        data = json.loads(make_parsable(res.text))
    except:
        raise Exception("Could not parse response")

    return data


def make_parsable(html):
    without_for_loop = re.sub(r"for\s*\(\s*;\s*;\s*\)\s*;\s*", "", html)

    # Handling multiple JSON objects in the same response
    maybe_multiple_objects = re.split(r"\}\r\n *\{", without_for_loop)
    if len(maybe_multiple_objects) == 1:
        return maybe_multiple_objects

    return "[" + "},{".join(maybe_multiple_objects) + "]"


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
    if id is not None:
        return re.sub(r"(fb)?id[:.]", "", id)
    else:
        return id


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
            and "target" in attachment_one["extensible_attachment"]["story_attachment"]
            and "__typename"
            in attachment_one["extensible_attachment"]["story_attachment"]["target"]
            and attachment_one["extensible_attachment"]["story_attachment"]["target"][
                "__typename"
            ]
            == "MessageLocation"
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
            "animated_gif_preview_url": attachment_two["image_data"]["animated_gif_preview_url"],
            "animated_webp_url": attachment_two["image_data"]["animated_webp_url"],
            "animated_webp_preview_url": attachment_two["image_data"]["animated_webp_preview_url"],
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

            "animated_image_size": attachment_one["share"]["media"]["animated_image_size"],
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

            "pack_id": blob["pack"]["id"] if "pack" in blob else None,
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

        return {
            "type": "share",
            "id": blob["legacy_attachment_id"],
            "url": blob["story_attachment"]["url"],

            "title": blob["story_attachment"]["title_with_entities"]["text"],
            "description": blob["story_attachment"]["description"]["text"]
            if "description" in blob["story_attachment"]
            else None,
            "source": blob["story_attachment"]["source"]["text"]
            if "source" in blob["story_attachment"]
            else None,

            "image": blob["story_attachment"]["media"]["image"]["uri"]
            if "image" in blob["story_attachment"]["media"]
            else None,
            "width": blob["story_attachment"]["media"]["image"]["width"]
            if "image" in blob["story_attachment"]["media"]
            else None,
            "height": blob["story_attachment"]["media"]["image"]["height"]
            if "image" in blob["story_attachment"]["media"]
            else None,
            "playable": blob["story_attachment"]["media"]["is_playable"]
            if "media" in blob["story_attachment"]
            else None,
            "duration": blob["story_attachment"]["media"]["playable_duration_in_ms"]
            if "media" in blob["story_attachment"]
            else None,
            "playable_url": blob["story_attachment"]["media"]["playable_url"]
            if "media" in blob["story_attachment"]
            else None,

            "subattachments": blob["story_attachment"]["subattachments"],
            "properties": properties,

            "facebook_url": blob["story_attachment"]["url"],
            "target": blob["story_attachment"]["target"],
            "style_list": blob["story_attachment"]["style_list"],
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
