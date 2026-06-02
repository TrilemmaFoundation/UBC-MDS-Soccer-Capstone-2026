# app/chatbot/views.py
import json
import sys
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from .llm_engine import ask_football_chatbot

# Add the repository root to sys.path to access the 'src' directory for sample prompts
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.chatbot.prompts import SAMPLE_TEST_QUESTIONS

def chat_view(request):
    """Renders the main chat workspace framework layout."""
    context = {
        "sample_questions": SAMPLE_TEST_QUESTIONS
    }
    return render(request, "chat.html", context)

def get_response(request):
    """Processes message requests and injects the corresponding response block back to HTMX."""
    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        advanced_mode = request.POST.get("advanced_mode") == "on"
        
        if not user_text:
            return JsonResponse({"error": "Empty message"}, status=400)
            
        response_data = ask_football_chatbot(user_text)
        
        # Format query data as a readable JSON string if it exists
        query_data_raw = response_data.get("query_data")
        formatted_data = None
        
        if query_data_raw:
            if isinstance(query_data_raw, list) and len(query_data_raw) > 50:
                query_data_raw = query_data_raw[:50]
                query_data_raw.append({"_note": "Data truncated to 50 rows for display purposes."})
            formatted_data = json.dumps(query_data_raw, indent=2, default=str)
        
        # Send both user input context and output back to the target canvas window element
        context = {
            "user_message": user_text,
            "ai_message": response_data.get("answer"),
            "sql_query": response_data.get("sql_query"),
            "query_data": formatted_data,
            "advanced_mode": advanced_mode
        }
        return render(request, "chat_message.html", context)
