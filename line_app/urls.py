from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('callback/', views.callback, name='callback'),
    path('register-employee/', views.register_employee, name='register_employee'),
]
