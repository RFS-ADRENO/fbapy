# fbapy documentation

## Table of Contents

-   [Login](#login)
-   [Login Options](#login-options)
-   [API](#api)
    -   [listen_mqtt](#listen_mqtt)
    -   [send_message](#send_message)
    -   [send_sticker](#send_sticker)
    -   [edit_message](#edit_message)
-   [GRAPHQL API](#graphql-api)
    -   [Change Bio](#change-bio)
    -   [Set Profile Picture](#set-profile-picture)
    -   [share story](#share-story)
    -   [Create new group](#create-new-group)
-   [HTTP API](#http-api)

## Login

Using base64 encoded appstate from [c3c-fbstate](https://github.com/c3cbot/c3c-fbstate)

**Arguments**

-   `appstate` - base64 encoded appstate
-   `options` - login options, see [below](#login-options)

**Returns**

-   `api` - API object

**Example**

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

## Login Options

| Option            | Type    | Default | Description                              |
| ----------------- | ------- | ------- | ---------------------------------------- |
| `self_listen`     | boolean | false   | allow bot to listen to its own events    |
| `listen_events`   | boolean | true    | enable other events to be listened to    |
| `user_agent`      | string  |         | user agent to login with                 |
| `update_presence` | boolean | false   | set to true to disable presence listener |
| `online`          | boolean | true    | set account online status                |

## API

### listen_mqtt

Listen to MQTT events

**Note**

-   This method is blocking, non-blocking is not available yet

**Arguments**

-   `callback` - callback function to be called when event is received

**Example**

```python
def callback(event, api):
    if (
        event["type"] == CONSTS.EVENTS.MESSAGE or
        event["type"] == CONSTS.EVENTS.MESSAGE_REPLY
    ):
        print(f"Message from {event['sender']}: {event['body']}")

api.listen_mqtt(callback)
```

**Event Types**

An event is a dictionary, it has a `type` key that specifies the event type

| Type                             | Description           |
| -------------------------------- | --------------------- |
| `CONSTS.EVENTS.MESSAGE`          | message received      |
| `CONSTS.EVENTS.MESSAGE_REPLY`    | message replied to    |
| `CONSTS.EVENTS.MESSAGE_REACTION` | message reacted to    |
| `CONSTS.EVENTS.MESSAGE_UNSEND`   | message unsent        |
| `CONSTS.EVENTS.TYP`              | someone is typing     |
| `CONSTS.EVENTS.PRESENCE`         | presence received     |
| `CONSTS.EVENTS.READ_RECEIPT `    | read receipt received |
| `CONSTS.EVENTS.EVENT`            | other event received  |

**Other Event Dictionary**

| Key                | Type           | Description                              |
| ------------------ | -------------- | ---------------------------------------- |
| `type`             | string         | event type, always `CONSTS.EVENTS.EVENT` |
| `thread_id`        | string         | thread id of the event                   |
| `log_message_type` | string         | specific event type                      |
| `log_message_data` | dict           | specific event data                      |
| `timestamp`        | string<br>None | timestamp of the event                   |
| `author`           | string<br>None | author of the event                      |
| `participant_ids`  | list[string]   | list of participant ids                  |

**log_message_type**

| Type                             | Description               |
| -------------------------------- | ------------------------- |
| `CONSTS.LOG_MESSAGE.SUBSCRIBE`   | someone joined the thread |
| `CONSTS.LOG_MESSAGE.UNSUBSCRIBE` | someone left the thread   |
| `CONSTS.LOG_MESSAGE.THEME`       | theme changed             |
| `CONSTS.LOG_MESSAGE.ICON`        | icon changed              |
| `CONSTS.LOG_MESSAGE.NICKNAME`    | nickname changed          |
| `CONSTS.LOG_MESSAGE.ADMINS`      | admins status changed     |
| `CONSTS.LOG_MESSAGE.POLL`        | poll created/updated      |
| `CONSTS.LOG_MESSAGE.APPROVAL`    | approval mode changed     |
| `CONSTS.LOG_MESSAGE.CALL`        | call started/updated      |
| `CONSTS.LOG_MESSAGE.NAME`        | thread name changed       |
| `CONSTS.LOG_MESSAGE.IMAGE`       | thread image changed      |
| `CONSTS.LOG_MESSAGE.PINNED`      | pinned message changed    |

---

### send_message

Send message, must listen to MQTT

**Arguments**

| Argument     | Type                                                                         | Description                                              |
| ------------ | ---------------------------------------------------------------------------- | -------------------------------------------------------- |
| `text`       | string<br>None                                                               | message to be sent<br>Required if `attachment` is `None` |
| `mention`    | dict<br>list[dict]<br>None                                                   | mention data                                             |
| `attachment` | BufferedReader<br>tuple[string, BufferedReader, string]<br>list[...]<br>None | attachment(s) to be sent<br>Required if `text` is `None` |
| `thread_id`  | string                                                                       | Required. thread id to send message to                   |
| `message_id` | string<br>None                                                               | message id to reply to                                   |
| `callback`   | function<br>None                                                             | callback function to be called when the request is done  |

**Example**

Specify callback function

```python
def cb(data, error):
    if error is not None:
        print(f"Error: {error}")
    else:
        print(f"Data: {data}")
```

Send text message

```python
api.send_message(
    text="Hello World!",
    thread_id="0000000000000000",
    callback=cb,
)
```

Mention someone

```python
api.send_message(
    text="Hello @David!",
    mention={
        "id": "0000000000000000",
        "tag": "@David",
    },
    thread_id="0000000000000000",
    callback=cb,
)
```

Mention multiple people

```python
api.send_message(
    text="Hello @David and @John!",
    mention=[
        {
            "id": "0000000000000000",
            "tag": "@David",
        },
        {
            "id": "0000000000000000",
            "tag": "@John",
        },
    ],
    thread_id="0000000000000000",
    callback=cb,
)
```

Mention with custom offset

```python
api.send_message(
    text="Not this @David, but this @David!",
    mention={
        "id": "0000000000000000",
        "tag": "@David",
        "offset": 26
    },
    thread_id="0000000000000000",
    callback=cb,
)
```

Send attachment

```python
api.send_message(
    attachment=(
        "image/png",
        open("image.png", "rb"),
        "image.png",
    ),
    thread_id="0000000000000000",
    callback=cb,
)
```

send multiple attachments

```python
api.send_message(
    attachment=[
        (
            "image/png",
            open("image.png", "rb"),
            "image.png",
        ),
        (
            "image/png",
            open("image.png", "rb"),
            "image.png",
        ),
    ],
    thread_id="0000000000000000",
    callback=cb,
)
```

---

### send_sticker

Send sticker, must listen to MQTT

**Arguments**

| Argument     | Type             | Description                                             |
| ------------ | ---------------- | ------------------------------------------------------- |
| `sticker_id` | int              | Required. sticker id to send                            |
| `thread_id`  | string           | Required. thread id to send message to                  |
| `message_id` | string<br>None   | message id to reply to                                  |
| `callback`   | function<br>None | callback function to be called when the request is done |

**Example**

Specify callback function

```python
def cb(data, error):
    if error is not None:
        print(f"Error: {error}")
    else:
        print(f"Data: {data}")
```

Send sticker

```python
api.send_sticker(
    sticker_id=554423694645485,
    thread_id="0000000000000000",
    callback=cb,
)
```

---

### edit_message

Edit message, must listen to MQTT

**Arguments**

| Argument     | Type             | Description                                             |
| ------------ | ---------------- | ------------------------------------------------------- |
| `message_id` | string           | Required. message id to edit                            |
| `text`       | string           | message to be edited                                    |
| `callback`   | function<br>None | callback function to be called when the request is done |

**Example**

Specify callback function

```python
def cb(data, error):
    if error is not None:
        print(f"Error: {error}")
    else:
        print(f"Data: {data}")
```

Edit message

```python
api.edit_message(
    message_id="mid.$xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    text="Hello World!",
    callback=cb,
)
```

## GRAPHQL API

API that uses GraphQL instead of MQTT

**Todo**

-   [ ] Document return values

### Change Bio

**Arguments**

-   `bio_content` - new bio
-   `publish_bio` - set to true to publish bio

**Example**

```python
api.graphql.change_bio(
    bio_content="Hello World!",
    publish_bio=True,
)
```

---

### Set Profile Picture

**Arguments**

-   `avatar` - File tuple

**Example**

```python
api.graphql.set_profile_picture(
    avatar=(
        "new_avatar.png",
        open("new_avatar.png", "rb"),
        "image/png",
    ),
)
```

---

### Share Story

**Arguments**

-   `story` - Text to be shared
-   `preset_id` - Preset id
-   `font_id` - Font id

**Example**

```python
api.graphql.share_story(
    story="Hello World!",
    preset_id=CONSTS.LIST_COLORS[0],
    font_id=CONSTS.LIST_FONTS[0],
)
```

---

### Create new group

**Arguments**

-   `title` - Group title
-   `participants` - List of participant ids

**Example**

```python
api.graphql.create_new_group(
    title="Hello World!",
    participants=[
        "0000000000000000",
        "0000000000000000",
    ],
)
```

## HTTP API

**Note**

-   Does not require MQTT listener
-   For most cases, you should use the MQTT API instead

**Todo**

-   [ ] Documentation
