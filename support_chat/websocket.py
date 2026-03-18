import json
import asyncio
from uuid import UUID
from .services import save_message
from .redis_client import redis_client
from .models import Conversation
from .pubsub_manager import pubsub_manager
from .bot_service import get_bot_reply


async def ws_send(send, type: str, data: dict = None, error: str = None, code: int = None):
    payload = {"type": type}
    if data:
        payload.update(data)
    if error:
        payload["error"] = error
    if code:
        payload["code"] = code
    await send({"type": "websocket.send", "text": json.dumps(payload)})


async def chat_ws(scope, receive, send):
    try:
        conversation_uuid = scope["path"].rstrip("/").split("/")[-1]
        UUID(conversation_uuid)
    except Exception:
        await send({"type": "websocket.close", "code": 4400})
        return

    conversation = await Conversation.objects.filter(
        uuid=conversation_uuid
    ).values("id", "client_id", "operator_id", "bot_enabled").afirst()

    if not conversation:
        await send({"type": "websocket.close", "code": 4404})
        return

    conversation_id = conversation["id"]
    bot_enabled = conversation["bot_enabled"]
    allowed_ids = {conversation["client_id"], conversation["operator_id"]}
    allowed_ids.discard(None)

    channel = f"chat:{conversation_uuid}"
    queue = await pubsub_manager.subscribe(channel)

    await send({"type": "websocket.accept"})
    await ws_send(send, "connected", {"conversation_uuid": conversation_uuid})

    async def redis_listener():
        try:
            while True:
                data = await queue.get()
                await send({"type": "websocket.send", "text": data})
        except asyncio.CancelledError:
            pass

    listener_task = asyncio.create_task(redis_listener())

    async def handle_bot(user_text: str):
        typing_payload = json.dumps({"type": "typing", "sender_type": "bot"})
        await redis_client.publish(channel, typing_payload)
        print(f"[BOT] typing published to {channel}")

        try:
            reply_text, message = await get_bot_reply(conversation_id, user_text)
            print(f"[BOT] reply: {reply_text[:50]}")
        except Exception as e:
            print(f"[BOT] error: {e}")
            return

        payload = json.dumps({
            "type": "message",
            "conversation_uuid": conversation_uuid,
            "text": message.text,
            "sender_id": message.sender_id,
            "sender_type": message.sender_type,
            "created_at": message.created_at.isoformat()
        })
        await redis_client.publish(channel, payload)
        print(f"[BOT] message published to {channel}")

    try:
        while True:
            event = await receive()

            if event["type"] == "websocket.disconnect":
                break

            if event["type"] != "websocket.receive":
                continue

            try:
                data = json.loads(event.get("text", "{}"))
            except json.JSONDecodeError:
                await ws_send(send, "error", error="invalid json", code=400)
                continue

            sender_id = data.get("sender_id")
            sender_type = data.get("sender_type")

            if not sender_id or not sender_type:
                await ws_send(send, "error", error="missing fields", code=400)
                continue

            if int(sender_id) not in allowed_ids:
                await ws_send(send, "error", error="forbidden", code=403)
                continue

            message_type = data.get("type")

            if message_type == "message":
                text = data.get("text")

                if not text:
                    await ws_send(send, "error", error="text is required", code=400)
                    continue

                try:
                    message = await save_message(
                        conversation_uuid,
                        sender_type,
                        sender_id,
                        text
                    )
                except Exception as e:
                    print(f"save_message error: {e}")
                    await ws_send(send, "error", error="internal error", code=500)
                    continue

                payload = json.dumps({
                    "type": "message",
                    "conversation_uuid": conversation_uuid,
                    "text": message.text,
                    "sender_id": message.sender_id,
                    "sender_type": message.sender_type,
                    "created_at": message.created_at.isoformat()
                })
                await redis_client.publish(channel, payload)

                if bot_enabled:
                    asyncio.create_task(handle_bot(text))

            else:
                await ws_send(send, "error", error="unknown message type", code=400)

    finally:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        await pubsub_manager.unsubscribe(channel, queue)