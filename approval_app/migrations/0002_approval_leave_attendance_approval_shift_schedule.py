# Generated by Django 5.1.4 on 2025-03-05 10:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('approval_app', '0001_initial'),
        ('attendance_app', '0009_remove_leaveattendance_approval_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='approval',
            name='leave_attendance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='leave_attendance_id', to='attendance_app.leaveattendance'),
        ),
        migrations.AddField(
            model_name='approval',
            name='shift_schedule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shift_schedule_id', to='attendance_app.shiftschedule'),
        ),
    ]
