from ..utils import DefaultFuncs, generate_offline_threading_id, generate_timestamp_relative, generate_threading_id, get_signature_id
import time
from requests import Response

allowed_keys = ["attachment","url","sticker","emoji","emojiSize","body","mentions","location"]

def send_message(default_funcs: DefaultFuncs, ctx: dict):
		def send_content(form: dict, thread_id: str, is_group: bool, message_and_otid: str):
			if is_group:
				form["thread_fbid"] = thread_id
			else:
				form["specific_to_list[0]"] = "fbid:" + thread_id
				form["specific_to_list[1]"] = "fbid:" + ctx["user_id"]
				form["other_user_fbid"] = thread_id

			res: Response = default_funcs.post_with_defaults("https://www.facebook.com/messaging/send/", form)
			print(res.text)
				

		def send(msg: str | dict, thread_id: str, reply_to_message: str = None, is_group: bool = None):
			is_group = is_group if type(is_group) is bool else len(thread_id) > 15

			if not is_valid_msg(msg):
				raise ValueError("Message must be string or dict, not " + str(type(msg)))
			
			

			if type(msg) is str:
				msg = {"body": msg}

			disallowed_keys = [key for key in msg.keys() if key not in allowed_keys]

			if len(disallowed_keys) > 0:
				raise ValueError("Disallowed keys: " + str(disallowed_keys))
			
			message_and_otid = generate_offline_threading_id()

			form = {
				"client": "mercury",
				"action_type": "ma-type:user-generated-message",
				"author": "fbid:" + ctx["user_id"],
				"timestamp": int(time.time() * 1000),
				"timestamp_absolute": "Today",
				"timestamp_relative": generate_timestamp_relative(),
				"timestamp_time_passed": "0",
				"is_unread": False,
				"is_cleared": False,
				"is_forward": False,
				"is_filtered_content": False,
				"is_filtered_content_bh": False,
				"is_filtered_content_account": False,
				"is_filtered_content_quasar": False,
				"is_filtered_content_invalid_app": False,
				"is_spoof_warning": False,
				"source": "source:chat:web",
				"source_tags[0]": "source:chat",
				"body": msg["body"] if "body" in msg else "",
				"html_body": False,
				"ui_push_phase": "V3",
				"status": "0",
				"offline_threading_id": message_and_otid,
				"message_id": message_and_otid,
				"threading_id": generate_threading_id(ctx["client_id"]),
				"ephemeral_ttl_mode:": "0",
				"manual_retry_cnt": "0",
				# "has_attachment": bool(msg["attachment"] or msg["url"] or msg["sticker"]),
				"has_attachment": False,
				"signatureID": get_signature_id(),
				"replied_to_message_id": reply_to_message
			}

			send_content(form, thread_id, is_group, message_and_otid)

		return send

def is_valid_msg(msg):
	return type(msg) is dict or type(msg) is str
