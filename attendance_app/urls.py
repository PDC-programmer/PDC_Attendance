from django.urls import path
from . import views

urlpatterns = [
    path('leave-request/', views.leave_request_view, name='leave_request'),
    path('leave-request-auth/', views.leave_request_view_auth, name='leave_request_auth'),
    path('get-leave-types/', views.get_leave_types, name='get_leave_types'),
    path('get-leave-balances/', views.get_leave_balances, name='get_leave_balances'),
    path('get-staff/', views.get_staff, name='get_staff'),
    path('get-leave-attendances/', views.get_leave_attendances, name='get_leave_attendances'),
    path("leave-request-detail/<int:leave_id>/", views.leave_request_detail, name="leave_request_detail"),

    # New routes for leave requests overview and batch actions
    path('leave-requests-list/', views.leave_requests_list, name='leave_requests_list'),
    path('leave-requests-approval/', views.leave_requests_approval, name='leave_requests_approval'),
    path('batch-action/', views.batch_action, name='batch_action'),
]
