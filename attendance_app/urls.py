from django.urls import path
from .views import leave_request_view, get_leave_types

urlpatterns = [
    path('leave-request/', leave_request_view, name='leave_request'),
    path('get-leave-types/', get_leave_types, name='get_leave_types'),
]