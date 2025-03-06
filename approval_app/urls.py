from django.urls import path
from .views import *

urlpatterns = [
    path("approval-list/", approval_list, name="approval_list"),
    path("approval-list-request-user/", approval_list_request_user, name="approval_list_request_user"),
    path("approve/<int:approval_id>/<str:action>/", approve_request, name="approve_request"),
    path("bulk-update/", bulk_approve_requests, name="bulk_approve_requests"),
    path("bulk-cancel/", bulk_cancel_requests, name="bulk_cancel_requests"),
]
