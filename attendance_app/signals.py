from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import LeaveAttendance, LeaveBalance


@receiver(pre_save, sender=LeaveAttendance)
def track_previous_status(sender, instance, **kwargs):
    """
    เก็บสถานะก่อนหน้าของ LeaveAttendance
    """
    if instance.pk:
        # ดึงสถานะก่อนหน้าจากฐานข้อมูล
        previous_instance = LeaveAttendance.objects.get(pk=instance.pk)
        instance.previous_status = previous_instance.status
    else:
        # สำหรับการสร้างใหม่ ไม่มีสถานะก่อนหน้า
        instance.previous_status = None


@receiver(post_save, sender=LeaveAttendance)
def update_leave_balance(sender, instance, **kwargs):
    """
    ปรับปรุง LeaveBalance ตามสถานะใหม่
    """
    num_days = (instance.end_date - instance.start_date).days + 1

    # ค้นหา LeaveBalance ที่เกี่ยวข้อง
    leave_balance = LeaveBalance.objects.filter(user=instance.user, leave_type=instance.leave_type).first()

    if instance.status == 'approved':
        if leave_balance:
            if leave_balance.remaining_days >= num_days:
                # หักจำนวนวันเมื่อสถานะเปลี่ยนเป็น approved
                leave_balance.remaining_days -= num_days
                leave_balance.save()
            else:
                raise ValueError("Remaining leave days are insufficient.")

    elif instance.status == 'cancelled' and instance.previous_status == 'approved':
        if leave_balance:
            # คืนจำนวนวันเมื่อยกเลิก (เฉพาะที่เคยอนุมัติแล้วเท่านั้น)
            leave_balance.remaining_days += num_days
            leave_balance.save()
