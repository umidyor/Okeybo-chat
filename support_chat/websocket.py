# import json
# import asyncio
# from uuid import UUID
# from asgiref.sync import sync_to_async
# from .services import save_message
# from .redis_client import redis_client
# from .models import Conversation
#
#
# async def chat_ws(scope, receive, send):
#     try:
#         conversation_uuid = scope["path"].rstrip("/").split("/")[-1]
#         UUID(conversation_uuid)
#     except Exception:
#         await send({"type": "websocket.close", "code": 4400})
#         return
#
#     conversation = await sync_to_async(
#         Conversation.objects.filter(uuid=conversation_uuid).first
#     )()
#
#     if not conversation:
#         await send({"type": "websocket.close", "code": 4404})
#         return
#
#     channel = f"chat:{conversation_uuid}"
#     pubsub = redis_client.pubsub()
#
#     await send({"type": "websocket.accept"})
#     await pubsub.subscribe(channel)
#
#     async def redis_listener():
#         try:
#             async for message in pubsub.listen():
#                 if message["type"] == "message":
#                     await send({
#                         "type": "websocket.send",
#                         "text": message["data"]
#                     })
#         except asyncio.CancelledError:
#             pass
#
#     listener_task = asyncio.create_task(redis_listener())
#
#     try:
#         while True:
#             event = await receive()
#
#             if event["type"] == "websocket.disconnect":
#                 break
#
#             if event["type"] != "websocket.receive":
#                 continue
#
#             try:
#                 data = json.loads(event.get("text", "{}"))
#             except json.JSONDecodeError:
#                 continue
#
#             text = data.get("text")
#             sender_id = data.get("sender_id")
#             sender_type = data.get("sender_type")
#
#             if not text or not sender_id or not sender_type:
#                 continue
#
#             try:
#                 message = await save_message(
#                     conversation_uuid,
#                     sender_type,
#                     sender_id,
#                     text
#                 )
#             except Exception:
#                 continue
#
#             payload = json.dumps({
#                 "type": "message",
#                 "conversation_uuid": conversation_uuid,
#                 "text": message.text,
#                 "sender_id": message.sender_id,
#                 "sender_type": message.sender_type,
#                 "created_at": message.created_at.isoformat(),
#             })
#
#             await redis_client.publish(channel, payload)
#
#     finally:
#         listener_task.cancel()
#         try:
#             await listener_task
#         except asyncio.CancelledError:
#             pass
#         try:
#             await pubsub.unsubscribe(channel)
#         except Exception:
#             pass
#         try:
#             await pubsub.close()
#         except Exception:
#             pass

import json
import asyncio
from uuid import UUID
from asgiref.sync import sync_to_async
from .services import save_message
from .redis_client import redis_client
from .models import Conversation


async def chat_ws(scope, receive, send):
    try:
        conversation_uuid = scope["path"].rstrip("/").split("/")[-1]
        UUID(conversation_uuid)
    except Exception:
        await send({"type": "websocket.close", "code": 4400})
        return

    conversation = await sync_to_async(
        Conversation.objects.filter(uuid=conversation_uuid).first
    )()

    if not conversation:
        await send({"type": "websocket.close", "code": 4404})
        return

    channel = f"chat:{conversation_uuid}"
    pubsub = redis_client.pubsub()

    await send({"type": "websocket.accept"})
    await pubsub.subscribe(channel)

    async def redis_listener():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await send({
                        "type": "websocket.send",
                        "text": message["data"]
                    })
        except asyncio.CancelledError:
            pass

    listener_task = asyncio.create_task(redis_listener())

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
                continue

            message_type = data.get("type")

            if message_type == "message":
                text = data.get("text")
                sender_id = data.get("sender_id")
                sender_type = data.get("sender_type")

                if not text or not sender_id or not sender_type:
                    continue

                try:
                    message = await save_message(
                        conversation_uuid,
                        sender_type,
                        sender_id,
                        text
                    )
                except Exception:
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

            elif message_type == "file":
                payload = json.dumps({
                    "type": "file",
                    "conversation_uuid": conversation_uuid,
                    "file_url": data.get("file_url"),
                    "file_name": data.get("file_name"),
                    "file_size": data.get("file_size"),
                    "file_type": data.get("file_type"),
                    "sender_id": data.get("sender_id"),
                    "sender_type": data.get("sender_type"),
                    "created_at": data.get("created_at")
                })

                await redis_client.publish(channel, payload)

    finally:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass