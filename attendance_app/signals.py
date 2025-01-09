from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LeaveAttendance, LeaveBalance
from datetime import timedelta

@receiver(post_save, sender=LeaveAttendance)
def update_leave_balance(sender, instance, **kwargs):
    if instance.status == 'approved':
        # คำนวณจำนวนวันลา
        num_days = (instance.end_date - instance.start_date).days + 1

        # ค้นหา LeaveBalance ที่เกี่ยวข้อง
        leave_balance = LeaveBalance.objects.filter(user=instance.user, leave_type=instance.leave_type).first()

        if leave_balance:
            if leave_balance.remaining_days >= num_days:
                # หักจำนวนวันจาก remaining_days
                leave_balance.remaining_days -= num_days
                leave_balance.save()
            else:
                # Handle กรณีวันที่คงเหลือไม่พอ
                raise ValueError("Remaining leave days are insufficient.")
