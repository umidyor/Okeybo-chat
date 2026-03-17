from django.urls import path
from .views import StartChatView,UploadMediaView,ChatHistoryView

urlpatterns = [
    path("start/", StartChatView.as_view(), name="start_chat"),
    path("upload/", UploadMediaView.as_view()),
    path("history/", ChatHistoryView.as_view())

]