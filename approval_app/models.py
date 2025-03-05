from django.db import models
from user_app.models import User
from attendance_app.models import *
import os
from datetime import datetime, time


def leave_request_image_path(instance, filename):
    return os.path.join(f"leave_request_images/{instance.user.username}/{datetime.date(instance.start_datetime)}",
                        filename)


class Approval(models.Model):
    APPROVAL_TYPES = [
        ("leave", "ขอลา"),
        ("shift", "เปลี่ยนกะทำงาน"),
    ]

    STATUS_CHOICES = [
        ("pending", "รออนุมัติ"),
        ("approved", "อนุมัติ"),
        ("rejected", "ปฏิเสธ"),
    ]

    SHIFT_DAY_CHOICES = [
        ('working_day', 'วันทำงาน'),
        ('day_off', 'วันหยุดของพนักงาน'),
        ('public_holiday', 'วันหยุดนักขัตฤกษ์')
    ]

    leave_attendance = models.ForeignKey(LeaveAttendance, on_delete=models.DO_NOTHING,
                                         related_name="leave_attendance_id", null=True, blank=True)
    shift_schedule = models.ForeignKey(ShiftSchedule, on_delete=models.DO_NOTHING, related_name="shift_schedule_id",
                                       null=True, blank=True)
    request_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="approval_requests")
    approve_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="approval_approver", null=True,
                                     blank=True)
    approval_type = models.CharField(max_length=10, choices=APPROVAL_TYPES, null=True, blank=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.DO_NOTHING, null=True, blank=True)  # ถ้าเป็นการลา
    shift = models.ForeignKey(Shift, on_delete=models.DO_NOTHING, null=True, blank=True)  # ถ้าเป็นการเปลี่ยนกะ
    date = models.DateField(null=True, blank=True)  # ใช้ได้ทั้งกรณีลาและเปลี่ยนกะ
    shift_day = models.CharField(max_length=50, choices=SHIFT_DAY_CHOICES,
                                 null=True, blank=True)
    start_datetime = models.DateTimeField(null=True, blank=True)  # สำหรับการลา
    end_datetime = models.DateTimeField(null=True, blank=True)  # สำหรับการลา
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    image = models.ImageField(upload_to=leave_request_image_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.request_user.username} - {self.approval_type} ({self.status})"
