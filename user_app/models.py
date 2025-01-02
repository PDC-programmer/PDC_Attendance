from django.contrib.auth.models import AbstractUser
from django.db import models
import os


def user_image_path(instance, filename):
    return os.path.join(f"user_images/{instance.username}", filename)


class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    mobile = models.CharField(max_length=50, null=True, blank=True)
    position = models.ForeignKey('Position', on_delete=models.DO_NOTHING, null=True, blank=True)
    image = models.ImageField(upload_to=user_image_path, null=True, blank=True)
    uid = models.CharField(max_length=500, null=True, blank=True)


class Position(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey('Department', on_delete=models.DO_NOTHING)

    # Many-to-Many relationship for approvers
    approvers = models.ManyToManyField(
        'self',
        through='Approval',
        symmetrical=False,
        related_name='approved_positions'
    )

    def __str__(self):
        return self.name


class Approval(models.Model):
    approver = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='approving_positions')
    approved = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='positions_to_approve')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.approver.name} approves {self.approved.name}"


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
