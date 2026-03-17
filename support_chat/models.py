import uuid
from django.db import models


class Conversation(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    client_id = models.BigIntegerField()
    operator_id = models.BigIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        default="open"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["client_id"]),
            models.Index(fields=["operator_id"]),
        ]



class Message(models.Model):

    MESSAGE_TYPES = (
        ("text", "Text"),
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("file", "File"),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender_type = models.CharField(max_length=10)
    sender_id = models.IntegerField()

    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPES,
        default="text"
    )

    text = models.TextField(
        null=True,
        blank=True
    )

    file = models.FileField(
        upload_to="chat/",
        null=True,
        blank=True
    )

    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    file_size = models.IntegerField(
        null=True,
        blank=True
    )

    file_type = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_read = models.BooleanField(
        default=False
    )

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]