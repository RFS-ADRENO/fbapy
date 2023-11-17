from fcapy.utils import DefaultFuncs

from fcapy.apis.send_message import send_message
from fcapy.apis.listen_mqtt import listen_mqtt

class API:
    def __init__(self, default_funcs: DefaultFuncs, ctx: dict):
        self.send_message = send_message(default_funcs, ctx)
        self.listen_mqtt = listen_mqtt(default_funcs, ctx)
