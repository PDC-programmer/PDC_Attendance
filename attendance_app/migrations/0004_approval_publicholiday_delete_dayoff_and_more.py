# Generated by Django 5.1.4 on 2025-02-19 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance_app', '0003_dayoff_shift_alter_leavebalance_leave_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Approval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, choices=[('leave', 'ขอลางาน'), ('shift_change', 'ขอเปลี่ยนเวลาทำงาน'), ('edit_time', 'ขอแก้ไขเวลาทำงาน')], max_length=50, null=True)),
                ('status', models.CharField(choices=[('approved', 'อนุมัติ'), ('pending', 'รออนุมัติ'), ('rejected', 'ปฏิเสธ'), ('cancelled', 'ยกเลิก')], default='pending', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PublicHoliday',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('date', models.DateField()),
                ('group', models.CharField(blank=True, choices=[('CN', 'สำนักงาน'), ('OP', 'สาขา')], max_length=50, null=True)),
            ],
        ),
        migrations.DeleteModel(
            name='DayOff',
        ),
        migrations.RemoveField(
            model_name='shiftschedule',
            name='availability',
        ),
        migrations.AddField(
            model_name='shiftschedule',
            name='shift_day',
            field=models.CharField(choices=[('working_day', 'วันทำงาน'), ('day_off', 'วันหยุดของพนักงาน'), ('public_holiday', 'วันหยุดนักขัตฤกษ์')], default='working', max_length=50),
        ),
        migrations.AddField(
            model_name='shiftschedule',
            name='time_in',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='shiftschedule',
            name='time_out',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
