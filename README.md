# fbapy
Unofficial Facebook Chat API for Python

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
  - [libmagic issue](#libmagic-issue)
- [Example Usage](#example-usage)
    - [Login](#login)
    - [Send Message (HTTP Method)](#send-message-http-method)
- [Testing](#testing)
- [Documentation](#documentation)
- [License](#license)


## Introduction

fbapy is a Python version of the Node.js package [@xaviabot/fca-unofficial](https://www.npmjs.com/package/@xaviabot/fca-unofficial). It is based on the forked deprecated version [fca-unoffical](https://www.npmjs.com/package/fca-unofficial), which itself is a fork of the deprecated version [facebook-chat-api](https://www.npmjs.com/package/facebook-chat-api).


fbapy acknowledges the contributions of the original authors of [facebook-chat-api](https://www.npmjs.com/package/facebook-chat-api), recognizes the efforts put into [fca-unoffical](https://www.npmjs.com/package/fca-unofficial), and explains that the Python version is based on the for [@xaviabot/fca-unofficial](https://www.npmjs.com/package/@xaviabot/fca-unofficial).


## Installation

fbapy is available on PyPI:

```bash
pip install fbapy
```

### libmagic issue

If you encounter an error like this:

`ImportError: failed to find libmagic.  Check your installation`

You need to install libmagic.

For Termux:
```bash
pkg install sox
```

For Other Platforms:
```bash
pip install python-magic-bin==0.4.14
```


## Example Usage

### Login

Using base64 encoded appstate from [c3c-fbstate](https://github.com/c3cbot/c3c-fbstate)

```python
from fbapy import *

client = Client()

api = client.login(
    appstate="YOUR_BASE64_ENCODED_APP_STATE",
    options={
        "user_agent": "YOUR_USER_AGENT",
    },
)
```

### Send Message (HTTP Method)

```python
api.send_message_http(
    msg="Hello World!",
    thread_id="0000000000000000",
)
```

## Testing

You can run `test.py` to test the package. Install packages from requirements.txt + python-dotenv first.

```bash
pip install -r requirements.txt
pip install python-dotenv
```

Then create a `.env` file in the root directory of the project and add the following:

```bash
APPSTATE="YOUR_BASE64_ENCODED_APP_STATE"
```

Then run `test.py`:

```bash
python test.py
```

Open a chat with the appstate account, try sending `?ping1`/`?ping2`, and you should get a reply `pong`

![Alt text](https://i.ibb.co/Mg3WZ3w/image-2024-01-18-221941325.png)

## Documentation

See [DOCS.md](DOCS.md) for more information.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
