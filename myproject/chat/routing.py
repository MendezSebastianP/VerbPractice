from django.urls import re_path
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(r"ws/chatgpt-demo/", consumers.ChatConsumer.as_asgi(), name="chatgpt_demo"),
]