from fbapy import *
client = Client()

api = client.login(
    appstate="YOUR_APPSTATE",
    options={
        "user_agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36"
    },
)
def callback(event, api: API):
    if event["type"]=="message":
        api.send_message(
            text=event["body"],
            thread_id=event["thread_id"],
            message_id=event["message_id"]
                            )
api.listen_mqtt(callback)
