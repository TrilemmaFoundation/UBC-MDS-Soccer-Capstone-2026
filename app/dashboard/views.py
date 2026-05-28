from django.shortcuts import render

def dashboard_view(request):
    """Renders the Looker Studio Dashboard view (Embedded via iframe)."""
    
    return render(request, "dashboard.html")