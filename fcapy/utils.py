import random
import time
import base64
import json
from datetime import datetime
from requests import Session, Response
import re
from typing import Dict


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

        print(f"Request failed with status code {res.status_code}. Retrying in {retry_time}ms...")

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
        raise Exception(f"parseAndCheckLogin got status code: {res.status_code}. Bailing out of trying to parse response.")
    
    data = None
    try:
        data = json.loads(make_parsable(res.text))
    except:
        raise Exception("Could not parse response")
    
    return data


def make_parsable(html):
    without_for_loop = re.sub(r'for\s*\(\s*;\s*;\s*\)\s*;\s*', '', html)

    # Handling multiple JSON objects in the same response
    maybe_multiple_objects = re.split(r'\}\r\n *\{', without_for_loop)
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
      return format(r, 'x') if c == 'x' else format((r & 0x3) | 0x8, 'x') if c == 'y' else c
    
    guid = ''.join(generate_random_char(c) if c != '-' else '-' for c in guid_template)
    return guid
