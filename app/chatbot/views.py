# app/chatbot/views.py
import json
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.html import escape
from .llm_engine import ask_football_chatbot

from .prompts import SUGGESTED_QUESTIONS
from .marts_data_dict import MARTS_DATA_DICT

def get_column_annotations():
    """Parses MARTS_DATA_DICT to create a mapping of column names to their descriptions."""
    annotations = {}
    for line in MARTS_DATA_DICT.split('\n'):
        if line.strip().startswith('| `'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                col_name = parts[1].strip('`')
                desc = parts[2]
                # Restrict to technical column names containing '_' to prevent over-annotating common English words
                if col_name and desc and '_' in col_name:
                    annotations[col_name] = desc
    return annotations

COL_ANNOTATIONS = get_column_annotations()

def annotate_columns(text):
    """Finds mart column names in text and wraps them in HTML for hover tooltips."""
    if not text:
        return text
    
    text = escape(text)
    if not COL_ANNOTATIONS:
        return text
        
    # Sort columns by length descending to ensure longer names are matched before substrings
    sorted_cols = sorted(COL_ANNOTATIONS.keys(), key=len, reverse=True)
    pattern = re.compile(r'\b(' + '|'.join(map(re.escape, sorted_cols)) + r')\b')
    
    def replacement_func(match):
        col = match.group(1)
        desc = escape(COL_ANNOTATIONS[col])
        return (
            f'<span class="relative group inline-block text-green-300 border-b border-dashed border-green-500 cursor-help">'
            f'{col}'
            f'<span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 w-64 bg-gray-900 text-white text-xs rounded py-1.5 px-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg border border-gray-700 text-center whitespace-normal font-sans leading-relaxed">'
            f'{desc}'
            f'</span></span>'
        )

    return pattern.sub(replacement_func, text)

def chat_view(request):
    """Renders the main chat workspace framework layout."""
    context = {
        "suggested_questions": SUGGESTED_QUESTIONS
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
            "ai_message": annotate_columns(response_data.get("answer")),
            "sql_query": response_data.get("sql_query"),
            "query_data": formatted_data,
            "advanced_mode": advanced_mode
        }
        return render(request, "chat_message.html", context)
