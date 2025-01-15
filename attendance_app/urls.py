from django.urls import path
from .views import (
    leave_request_view,
    get_leave_types,
    get_leave_balances,
    get_staff,
    get_leave_attendances,
    leave_request_detail,
    leave_request_view_auth
)

urlpatterns = [
    path('leave-request/', leave_request_view, name='leave_request'),
    path('leave-request-auth/', leave_request_view_auth, name='leave_request_auth'),
    path('get-leave-types/', get_leave_types, name='get_leave_types'),
    path('get-leave-balances/', get_leave_balances, name='get_leave_balances'),
    path('get-staff/', get_staff, name='get_staff'),
    path('get-leave-attendances/', get_leave_attendances, name='get_leave_attendances'),
    path("leave-request-detail/<int:leave_id>/", leave_request_detail, name="leave_request_detail"),
]
