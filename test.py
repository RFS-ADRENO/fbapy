import os
from os.path import join, dirname
from dotenv import load_dotenv

from fcapy import *

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

client = Client()

api = client.login(os.environ.get("APPSTATE"), options={
	"user_agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36"
})

PREFIX = "."

def callback(event, api: API):
  try:
    if event is not None:
      if event["type"] == "message" or event["type"] == "message_reply":
        body = event["body"] # guaranteed to exist

        
        if body.startswith(PREFIX):
          if body == PREFIX + "ping":
            api.send_message("pong", event["thread_id"], event["message_id"])
          elif body == PREFIX + "hi":
            api.send_message("hello", event["thread_id"], event["message_id"])
          elif body == PREFIX + "meow":
            api.send_message({"sticker": "554423694645485"}, event["thread_id"], event["message_id"])
          elif body == PREFIX + "where":
            api.send_message({"location": {"latitude": 10.764461306457537, "longitude": 106.66615124288597}}, event["thread_id"], event["message_id"])
          elif body == PREFIX + "share":
            api.share_story("Hello world")
          else:
            api.send_message("Unknown command", event["thread_id"], event["message_id"])

        if "attachments" in event and len(event["attachments"]) > 0:
          for attachment in event["attachments"]:
            if "preview_url" not in attachment or attachment["type"] == "video":
              print(f"Attachment: {attachment['type']} - {attachment['url']}")
            else:
              print(f"Attachment: {attachment['type']} - {attachment['preview_url']}")

            if attachment['type'] == "sticker":
              print("Sticker ID:", attachment['sticker_id'])


  except Exception as e:
    print(e)
    print(event)

api.listen_mqtt(callback)
