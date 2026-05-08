# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.chat_view, name="chat_home"),
    path("ask/", views.get_response, name="ask_chatbot"),
]