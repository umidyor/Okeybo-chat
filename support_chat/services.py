from .models import Message, Conversation
async def save_message(conversation_uuid, sender_type, sender_id, text):
    conversation = await Conversation.objects.aget(uuid=conversation_uuid)
    message = await Message.objects.acreate(
        conversation=conversation,
        sender_type=sender_type,
        sender_id=sender_id,
        text=text
    )
    return message