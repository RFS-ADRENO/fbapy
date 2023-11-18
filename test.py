import os
from os.path import join, dirname
from dotenv import load_dotenv

from fcapy.fcapy import *

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

client = Client()

api = client.login(os.environ.get("APPSTATE"), options={
	"user_agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36"
})

# api.send_message("hello from fcapy", "4228720243921825").
api.listen_mqtt()
