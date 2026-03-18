import time
import httpx,asyncio
from django.conf import settings
from .models import Conversation, Message, BotConfig

OPENAI_API_KEY = settings.OPENAI_API_KEY

SUMMARY_THRESHOLD = 20
LAST_MESSAGES_COUNT = 10

_prompt_cache = {"value": None, "updated_at": 0}
PROMPT_CACHE_TTL = 60


async def get_system_prompt() -> str:
    now = time.time()
    if _prompt_cache["value"] is None or now - _prompt_cache["updated_at"] > PROMPT_CACHE_TTL:
        config = await BotConfig.objects.filter(is_active=True).afirst()
        _prompt_cache["value"] = config.system_prompt if config else ""
        _prompt_cache["updated_at"] = now
    return _prompt_cache["value"]


async def get_history_and_summary(conversation_id: int):
    conversation = await Conversation.objects.filter(
        id=conversation_id
    ).values("ai_summary").afirst()

    messages = []
    async for m in Message.objects.filter(
        conversation_id=conversation_id,
        message_type="text"
    ).order_by("-id").values("sender_type", "text")[:LAST_MESSAGES_COUNT]:
        messages.append(m)

    messages.reverse()
    return conversation["ai_summary"], messages


async def get_message_count(conversation_id: int) -> int:
    from django.db.models import Count
    result = await Message.objects.filter(
        conversation_id=conversation_id
    ).acount()
    return result


async def save_bot_message(conversation_id: int, text: str) -> Message:
    return await Message.objects.acreate(
        conversation_id=conversation_id,
        sender_type="bot",
        sender_id=0,
        message_type="text",
        text=text
    )


async def update_summary(conversation_id: int, new_summary: str):
    await Conversation.objects.filter(
        id=conversation_id
    ).aupdate(ai_summary=new_summary)


async def _openai_request(messages: list) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": messages
            }
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def maybe_update_summary(
    conversation_id: int,
    current_summary: str | None,
    history: list
) -> str | None:
    count = await get_message_count(conversation_id)
    if count % SUMMARY_THRESHOLD != 0:
        return current_summary

    history_text = "\n".join(
        f"{m['sender_type']}: {m['text']}" for m in history
    )

    prompt = [
        {
            "role": "system",
            "content": (
                "Suhbat tarixini qisqacha xulosala. "
                "Asosiy mavzular, muammolar va yechimlarni saqla. "
                "300 tokendan oshmasin."
            )
        },
        {
            "role": "user",
            "content": (
                f"Oldingi xulosa:\n{current_summary or 'Yo`q'}\n\n"
                f"Yangi xabarlar:\n{history_text}"
            )
        }
    ]

    new_summary = await _openai_request(prompt)
    await update_summary(conversation_id, new_summary)
    return new_summary


async def get_bot_reply(conversation_id: int, user_text: str) -> tuple[str, Message]:
    system_prompt, (summary, history) = await asyncio.gather(
        get_system_prompt(),
        get_history_and_summary(conversation_id)
    )

    summary = await maybe_update_summary(conversation_id, summary, history)

    messages = [{"role": "system", "content": system_prompt}]

    if summary:
        messages.append({
            "role": "assistant",
            "content": f"Suhbat xulosasi: {summary}"
        })

    for m in history:
        role = "user" if m["sender_type"] == "client" else "assistant"
        messages.append({"role": role, "content": m["text"]})

    messages.append({"role": "user", "content": user_text})

    reply_text = await _openai_request(messages)
    message = await save_bot_message(conversation_id, reply_text)

    return reply_text, message