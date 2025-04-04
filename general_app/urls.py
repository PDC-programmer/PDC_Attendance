from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.log_in, name='log-in'),
    path('logout', views.log_out, name='log-out'),
    path('get-pending-leave-attendances/', views.get_pending_leave_attendances, name='get-pending-leave-attendances'),
]
