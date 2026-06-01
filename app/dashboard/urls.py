from django.urls import path
from .views import dashboard_view

urlpatterns = [
    # Dashboard app routes
    path("", dashboard_view, name="dashboard"),
]