from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # path("admin/", admin.site.urls),
    
    # Product 1: Looker Studio Dashboard (Embedded via iframe)
    path("dashboard/", include("dashboard.urls")),
    
    # Product 2: LLM Chatbot (Groq + Tool Calling)
    path("", include("chatbot.urls")),
    
    # API Endpoints
    # path("api/", include("api.urls")),
]