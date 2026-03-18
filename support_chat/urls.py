from django.urls import path
from .views import StartChatView,UploadMediaView,ChatHistoryView,ConversationListView,chat_demo_operator,chat_demo_client

urlpatterns = [
    path("start/", StartChatView.as_view(), name="start_chat"),
    path("upload/", UploadMediaView.as_view()),
    path("history/", ChatHistoryView.as_view()),
    path("conversations/", ConversationListView.as_view()),
    path("demo/client/<int:client_id>/", chat_demo_client, name="chat_demo_client"),
    path("demo/operator/<int:operator_id>/", chat_demo_operator, name="chat_demo_operator"),
]

