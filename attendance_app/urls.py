from django.urls import path
from .views import (
    leave_request_view,
    get_leave_types,
    get_leave_balances,
    get_staff,
    get_leave_attendances,
    leave_request_detail
)

urlpatterns = [
    path('leave-request/', leave_request_view, name='leave_request'),
    path('get-leave-types/', get_leave_types, name='get_leave_types'),
    path('get-leave-balances/<str:user_id>/', get_leave_balances, name='get_leave_balances'),
    path('get-staff/<str:user_id>/', get_staff, name='get_staff'),
    path('get-leave-attendances/<str:user_id>/', get_leave_attendances, name='get_leave_attendances'),
    path("leave-request-detail/<int:leave_id>/", leave_request_detail, name="leave_request_detail"),
]
