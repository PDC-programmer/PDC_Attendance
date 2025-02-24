from django.db import models
from django.utils.timezone import now


class ChatMessage(models.Model):
    sender = models.CharField(max_length=255)
    receiver = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)
    message_type = models.CharField(max_length=50, choices=[('sent', 'Sent'), ('received', 'Received')])

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.message[:50]}"
