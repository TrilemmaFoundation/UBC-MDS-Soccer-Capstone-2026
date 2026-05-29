from django.shortcuts import render
from django.conf import settings

def dashboard_view(request):
    """Renders the Looker Studio Dashboard view (Embedded via iframe)."""
    
    context = {
        "looker_studio_url": settings.LOOKER_STUDIO_URL
    }
    
    return render(request, "dashboard.html", context)