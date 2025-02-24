from django.urls import path
from .views import oho_chat_webhook

urlpatterns = [
    path('webhook/', oho_chat_webhook, name='oho_chat_webhook'),
]