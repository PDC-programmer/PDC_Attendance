# Generated by Django 5.1.4 on 2025-03-04 15:37

import approval_app.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('attendance_app', '0009_remove_leaveattendance_approval_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Approval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('approval_type', models.CharField(choices=[('leave', 'ขอลา'), ('shift', 'เปลี่ยนกะทำงาน')], max_length=10)),
                ('date', models.DateField()),
                ('start_datetime', models.DateTimeField(blank=True, null=True)),
                ('end_datetime', models.DateTimeField(blank=True, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'รออนุมัติ'), ('approved', 'อนุมัติ'), ('rejected', 'ปฏิเสธ')], default='pending', max_length=10)),
                ('image', models.ImageField(blank=True, null=True, upload_to=approval_app.models.leave_request_image_path)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('approve_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='approval_approver', to=settings.AUTH_USER_MODEL)),
                ('leave_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='attendance_app.leavetype')),
                ('request_user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='approval_requests', to=settings.AUTH_USER_MODEL)),
                ('shift', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='attendance_app.shift')),
            ],
        ),
    ]
