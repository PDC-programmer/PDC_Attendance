from django.urls import path
from . import views

urlpatterns = [
    path("staff/", views.manage_staff, name="add_staff"),
    path("staff/<int:staff_id>/", views.manage_staff, name="edit_staff"),
    path("get-staff-codes/", views.get_staff_codes, name="get_staff_codes"),
    path("staff-list/", views.staff_list, name="staff_list"),
    path('upload-profile/', views.upload_profile_image, name='upload-profile-image'),
]
