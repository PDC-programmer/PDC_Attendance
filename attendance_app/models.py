from django.db import models
from user_app.models import User


class LeaveType(models.Model):
    th_name = models.CharField(max_length=100, unique=True)
    en_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.th_name


class LeaveAttendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="request_user")
    approve_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="approve_user")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=[('approved', 'อนุมัติ'),
                                                      ('pending', 'รออนุมัติ'),
                                                      ('rejected', 'ปฏิเสธ'),
                                                      ('cancelled', 'ยกเลิก')],
                              default='pending')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.DO_NOTHING, default='1')

    def __str__(self):
        return f"{self.user.username}: {self.status} ({self.start_date} to {self.end_date})"


class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="leave_balances")
    total_days = models.FloatField(default=0)  # จำนวนวันที่มีสิทธิลา
    remaining_days = models.FloatField(default=0)  # จำนวนวันที่เหลือ

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.th_name}: {self.remaining_days} days remaining"

    def calculate_leave_balance(self):
        attendance = LeaveAttendance.objects.filter(
            user=self.user,
            status='approved',
            leave_type=self.leave_type,
        )

        leave_days = (attendance.end_date - attendance.start_date).days + 1

    def save(self, *args, **kwargs):
        self.remaining_days = self.calculate_leave_balance()
        super().save(*args, **kwargs)

        LeaveBalance.objects.filter(user=self.user).update(remaining_days=self.remaining_days)