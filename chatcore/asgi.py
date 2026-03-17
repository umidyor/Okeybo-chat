"""
ASGI config for chatcore project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chatcore.settings")

django_app = get_asgi_application()

from support_chat.websocket import chat_ws


async def application(scope, receive, send):

    if scope["type"] == "websocket":
        path = scope.get("path", "")

        if path.startswith("/ws/chat/"):
            await chat_ws(scope, receive, send)
            return
    await django_app(scope, receive, send)