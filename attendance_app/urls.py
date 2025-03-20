from django.urls import path
from . import views

urlpatterns = [
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


    path('leave-attendance/', views.leave_attendance_list, name='leave_attendance_list'),
    path('leave-attendance/export/excel/', views.export_leave_attendance_excel, name='export_leave_attendance_excel'),

    path("shift-schedule-bulk-update/", views.shift_schedule_bulk_update, name="shift_schedule_bulk_update"),
    path("shift-schedule-update/", views.shift_schedule_update, name="shift_schedule_update"),
    path('shift-schedule-view/', views.shift_schedule_view, name='shift_schedule_view'),
    path("shift-schedule-approve/", views.shift_schedule_approve, name="shift_schedule_approve"),
    path("shift-schedule-batch-approve/", views.shift_schedule_batch_approve, name="shift_schedule_batch_approve"),

    path("leave-balance/", views.leave_balance_list, name="leave_balance_list"),
    path("leave-balance/edit/<int:leave_balance_id>/", views.edit_leave_balance, name="edit_leave_balance"),
    path("leave-balance/import/", views.import_leave_balance, name="import_leave_balance"),

    path("search-attendance/", views.search_attendance, name="search_attendance"),
    path("search-attendance-detail/", views.employee_attendance_history, name="employee_attendance_history"),
    path("request-edit-time/", views.request_edit_time, name="request_edit_time"),

]
