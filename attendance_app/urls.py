from django.urls import path
from .views import leave_request_view, get_leave_types, get_leave_balances, get_staff

urlpatterns = [
    path('leave-request/', leave_request_view, name='leave_request'),
    path('get-leave-types/', get_leave_types, name='get_leave_types'),
    path('get-leave-balances/', get_leave_balances, name='get_leave_balances'),
    path('get-staff/', get_staff, name='get_staff'),
]
