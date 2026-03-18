from django.contrib import admin
from .models import Conversation, Message,BotConfig


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "client_id", "operator_id", "status", "created_at")
    search_fields = ("client_id", "operator_id")
    list_filter = ("status",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender_type", "sender_id", "created_at", "is_read")
    list_filter = ("sender_type", "is_read")
    search_fields = ("text",)

@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "is_active", "updated_at")