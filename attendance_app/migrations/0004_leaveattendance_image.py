# Generated by Django 5.1.4 on 2025-01-10 01:22

import attendance_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance_app', '0003_alter_leaveattendance_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaveattendance',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=attendance_app.models.leave_request_image_path),
        ),
    ]
