# app/chatbot/views.py
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from .llm_engine import ask_football_chatbot

def chat_view(request):
    """Renders the main chat workspace framework layout."""
    return render(request, "chat.html")

@csrf_protect
def get_response(request):
    """Processes message requests and injects the corresponding response block back to HTMX."""
    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        if not user_text:
            return JsonResponse({"error": "Empty message"}, status=400)
            
        answer = ask_football_chatbot(user_text)
        
        # Send both user input context and output back to the target canvas window element
        context = {
            "user_message": user_text,
            "ai_message": answer
        }
        return render(request, "chat_message.html", context)