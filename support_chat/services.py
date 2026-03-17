from asgiref.sync import sync_to_async
from .models import Message,Conversation

@sync_to_async
def save_message(conversation_uuid, sender_type, sender_id, text):
    conversation = Conversation.objects.get(uuid=conversation_uuid)

    message = Message.objects.create(
        conversation=conversation,
        sender_type=sender_type,
        sender_id=sender_id,
        text=text
    )

    return message