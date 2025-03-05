from django.urls import path
from .views import approval_list, approve_request, bulk_approve_requests

urlpatterns = [
    path("approval-list/", approval_list, name="approval_list"),
    path("approve/<int:approval_id>/<str:action>/", approve_request, name="approve_request"),
    path("bulk-update/", bulk_approve_requests, name="bulk_approve_requests"),
]
