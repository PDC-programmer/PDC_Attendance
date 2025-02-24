# Generated by Django 5.1.4 on 2025-02-19 18:17

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance_app', '0005_alter_shiftschedule_time_in_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shiftschedule',
            name='time_in',
        ),
        migrations.RemoveField(
            model_name='shiftschedule',
            name='time_out',
        ),
        migrations.AddField(
            model_name='shiftschedule',
            name='approve_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shift_schedules_approve_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='shiftschedule',
            name='status',
            field=models.CharField(choices=[('approved', 'อนุมัติ'), ('pending', 'รออนุมัติ'), ('rejected', 'ปฏิเสธ'), ('cancelled', 'ยกเลิก')], default='pending', max_length=50),
        ),
    ]
