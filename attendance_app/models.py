from django.db import models
from user_app.models import User
import os
from datetime import datetime, time


def leave_request_image_path(instance, filename):
    return os.path.join(f"leave_request_images/{instance.user.username}/{datetime.date(instance.start_datetime)}",
                        filename)


class LeaveType(models.Model):
    th_name = models.CharField(max_length=100, unique=True)
    en_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.th_name


class LeaveAttendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="request_user")
    approve_user = models.ForeignKey(User, on_delete=models.DO_NOTHING,
                                     related_name="approve_user")
    start_datetime = models.DateTimeField(null=True, blank=True)  # Change to DateTimeField for precise times
    end_datetime = models.DateTimeField(null=True, blank=True)  # Change to DateTimeField for precise times
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=[('approved', 'อนุมัติ'),
                                                      ('pending', 'รออนุมัติ'),
                                                      ('rejected', 'ปฏิเสธ'),
                                                      ('cancelled', 'ยกเลิก')],
                              default='pending')  
    leave_type = models.ForeignKey(LeaveType, on_delete=models.DO_NOTHING, default='1')
    image = models.ImageField(upload_to=leave_request_image_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # auto add created date time
    updated_at = models.DateTimeField(null=True, blank=True)  # Change to DateTimeField for precise times

    def __str__(self):
        return f"{self.user.username}: {self.status} ({self.start_datetime} to {self.end_datetime})"


class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.DO_NOTHING, related_name="leave_balances")
    total_hours = models.FloatField(default=0)  # Change to hours
    remaining_hours = models.FloatField(default=0)  # Change to hours
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # auto add created date time
    updated_at = models.DateTimeField(null=True, blank=True)  # Change to DateTimeField for precise times

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.th_name}: {self.remaining_hours} hours remaining"


class LeaveBalanceInitial(models.Model):
    staff_code = models.CharField(max_length=128, blank=True, null=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.DO_NOTHING, related_name="leave_balances_initial")
    total_hours = models.FloatField(default=0)  # Change to hours
    remaining_hours = models.FloatField(default=0)  # Change to hours


class Shift(models.Model):
    name = models.CharField(max_length=100, unique=True)
    morning_start = models.TimeField(default=time(9, 0))  # เวลาเริ่มต้นค่าเริ่มต้น 09:00 น.
    morning_end = models.TimeField(default=time(13, 0))  # เวลาสิ้นสุดค่าเริ่มต้น 13:00 น.
    afternoon_start = models.TimeField(default=time(14, 0))  # เวลาสิ้นสุดค่าเริ่มต้น 14:00 น.
    afternoon_end = models.TimeField(default=time(18, 0))  # เวลาสิ้นสุดค่าเริ่มต้น 18:00 น.
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # auto add created date time
    updated_at = models.DateTimeField(null=True, blank=True)  # Change to DateTimeField for precise times

    def __str__(self):
        return f"{self.name} ({self.morning_start} - {self.afternoon_end})"


class ShiftSchedule(models.Model):
    approve_user = models.ForeignKey(User, on_delete=models.DO_NOTHING,
                                     related_name="shift_schedules_approve_user", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="shift_schedules")
    shift = models.ForeignKey(Shift, on_delete=models.DO_NOTHING, related_name="shift_schedules")
    date = models.DateField()  # วันที่สำหรับกะนี้
    shift_day = models.CharField(max_length=50, choices=[('working_day', 'วันทำงาน'),
                                                         ('day_off', 'วันหยุดของพนักงาน'),
                                                         ('public_holiday', 'วันหยุดนักขัตฤกษ์')],
                                 default='working')
    status = models.CharField(max_length=50, choices=[('approved', 'อนุมัติ'),
                                                      ('pending', 'รออนุมัติ'),
                                                      ('rejected', 'ปฏิเสธ'),
                                                      ('cancelled', 'ยกเลิก')],
                              default='pending')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # auto add created date time
    updated_at = models.DateTimeField(null=True, blank=True)  # Change to DateTimeField for precise times

    def __str__(self):
        return f"{self.user.username} - {self.shift.name} on {self.date}"


class PublicHoliday(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    group = models.CharField(max_length=50, choices=[('CN', 'สำนักงาน'),
                                                     ('OP', 'สาขา')
                                                     ],
                             blank=True, null=True)
