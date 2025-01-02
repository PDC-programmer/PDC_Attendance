from django.db import models
from user_app.models import User


class LeaveAttendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="request_user")
    approve_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="approve_user")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=[('approved', 'Approved'),
                                                      ('pending', 'Pending'),
                                                      ('rejected', 'Rejected')],
                              default='pending')
    type = models.CharField(max_length=50, choices=[('sick_leave', 'ลาป่วย'),
                                                    ('annual_leave', 'ลาพักร้อน'),
                                                    ('absence_leave', 'ลากิจ'),
                                                    ('maternity_leave', 'ลาคลอด'),
                                                    ('bereavement_leave', 'ลาไปงานศพ')],
                            default='sick_leave')

    def __str__(self):
        return f"{self.user.username}: {self.status} ({self.start_date} to {self.end_date})"
