# views.py
from django.shortcuts import render
from django.http import JsonResponse
from .llm_engine import ask_football_chatbot

def chat_view(request):
    """Renders the main chat interface."""
    return render(request, "chat.html")

def get_response(request):
    if request.method == "POST":
        user_text = request.POST.get("message")
        answer = ask_football_chatbot(user_text)
        
        # Return a simple HTML fragment instead of JSON
        return render(request, "chat_message.html", {"message": answer})