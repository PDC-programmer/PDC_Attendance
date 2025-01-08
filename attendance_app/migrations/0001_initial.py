# Generated by Django 5.1.4 on 2025-01-08 10:45

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('approved', 'Approved'), ('pending', 'Pending'), ('rejected', 'Rejected')], default='pending', max_length=50)),
                ('type', models.CharField(choices=[('sick_leave', 'ลาป่วย'), ('annual_leave', 'ลาพักร้อน'), ('absence_leave', 'ลากิจ'), ('maternity_leave', 'ลาคลอด'), ('bereavement_leave', 'ลาไปงานศพ')], default='sick_leave', max_length=50)),
                ('approve_user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='approve_user', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='request_user', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
