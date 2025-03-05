from django.urls import path
from . import views

urlpatterns = [
    path('register-line-id/', views.register_line_id, name='register_line_id'),
    path('get-staff-info/<str:staff_code>/', views.get_staff_info, name='get_staff_info'),
    path('user-info/', views.user_info, name='user_info'),
    path('callback/', views.callback, name='callback'),
]
