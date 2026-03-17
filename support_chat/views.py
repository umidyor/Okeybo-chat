import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Conversation



import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Conversation,Message


@method_decorator(csrf_exempt, name="dispatch")
class StartChatView(View):

    def post(self, request):

        data = json.loads(request.body or "{}")

        client_id = data.get("client_id")
        operator_id = data.get("operator_id")

        if not client_id or not operator_id:
            return JsonResponse({
                "error": "client_id and operator_id are required"
            }, status=400)

        conversation = Conversation.objects.filter(
            client_id=client_id,
            operator_id=operator_id,
            status="open"
        ).first()

        if not conversation:
            conversation = Conversation.objects.create(
                client_id=client_id,
                operator_id=operator_id
            )

        return JsonResponse({
            "conversation_uuid": str(conversation.uuid)
        })

ALLOWED_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "application/pdf": "file",
    "application/msword": "file",
}


@method_decorator(csrf_exempt, name="dispatch")
class UploadMediaView(View):

    def post(self, request):

        conversation_uuid = request.POST.get("conversation_uuid")
        sender_id = request.POST.get("sender_id")
        sender_type = request.POST.get("sender_type")

        file = request.FILES.get("file")

        if not conversation_uuid or not sender_id or not sender_type:
            return JsonResponse({"error": "missing fields"}, status=400)

        if not file:
            return JsonResponse({"error": "file required"}, status=400)

        file_type = file.content_type

        if file_type not in ALLOWED_TYPES:
            return JsonResponse({"error": "file type not allowed"}, status=400)

        conversation = Conversation.objects.filter(
            uuid=conversation_uuid
        ).first()

        if not conversation:
            return JsonResponse({"error": "conversation not found"}, status=404)

        message = Message.objects.create(
            conversation=conversation,
            sender_id=sender_id,
            sender_type=sender_type,
            message_type=ALLOWED_TYPES[file_type],
            file=file,
            file_name=file.name,
            file_size=file.size,
            file_type=file_type
        )

        return JsonResponse({
            "message_id": message.id,
            "message_type": message.message_type,
            "file_url": message.file.url,
            "file_name": message.file_name,
            "file_size": message.file_size,
            "created_at": message.created_at.isoformat()
        })

@method_decorator(csrf_exempt, name="dispatch")
class ChatHistoryView(View):

    def get(self, request):

        conversation_uuid = request.GET.get("conversation_uuid")
        if not conversation_uuid:
            return JsonResponse(
                {"error": "conversation_uuid not provided"},
                status=400
            )

        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))

        if limit > 100:
            limit = 100

        conversation = Conversation.objects.filter(
            uuid=conversation_uuid
        ).values("id").first()

        if not conversation:
            return JsonResponse(
                {"error": "conversation not found"},
                status=404
            )

        messages = Message.objects.filter(
            conversation_id=conversation["id"]
        ).order_by("-id").values(
            "id",
            "message_type",
            "text",
            "file",
            "file_name",
            "file_size",
            "file_type",
            "sender_id",
            "sender_type",
            "is_read",
            "created_at"
        )[offset:offset + limit]

        data = []

        for m in messages:

            data.append({
                "id": m["id"],
                "message_type": m["message_type"],
                "text": m["text"],
                "file_url": m["file"] if m["file"] else None,
                "file_name": m["file_name"],
                "file_size": m["file_size"],
                "file_type": m["file_type"],
                "sender_id": m["sender_id"],
                "sender_type": m["sender_type"],
                "is_read": m["is_read"],
                "created_at": m["created_at"].isoformat()
            })

        return JsonResponse({
            "conversation_uuid": conversation_uuid,
            "limit": limit,
            "offset": offset,
            "messages": data
        })