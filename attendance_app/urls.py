from django.urls import path
from .views import leave_request_view

urlpatterns = [
    path('leave-request/', leave_request_view, name='leave_request'),
]