from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Approval
from attendance_app.models import LeaveAttendance, ShiftSchedule, EditTimeAttendance
from django.utils.timezone import now


@receiver(post_save, sender=Approval)
def update_attendance_or_shift(sender, instance, created, **kwargs):
    """
    เมื่อมีการบันทึก (save) Approval ให้ทำการเปลี่ยนแปลง LeaveAttendance หรือ ShiftSchedule
    """
    if instance.status == "approved":
        if instance.approval_type == "leave":
            # อัปเดต LeaveAttendance ตามคำขอ
            leave_attendance = LeaveAttendance.objects.filter(
                id=instance.leave_attendance.id
            ).first()
            if leave_attendance:
                leave_attendance.status = "approved"
                leave_attendance.updated_at = now()
                leave_attendance.save()

        elif instance.approval_type == "shift":
            # อัปเดต ShiftSchedule ตามคำขอ
            shift_schedule = ShiftSchedule.objects.filter(
                id=instance.shift_schedule.id
            ).first()

            if shift_schedule:
                shift_schedule.shift = instance.shift
                shift_schedule.shift_day = instance.shift_day
                shift_schedule.approve_user = instance.approve_user
                shift_schedule.status = "approved"
                shift_schedule.updated_at = now()
                shift_schedule.save()

        elif instance.approval_type == "edit_time":
            edit_attendance = EditTimeAttendance.objects.filter(
                date=instance.date, status="pending", approve_user=instance.approve_user, user=instance.request_user,
                branch=instance.branch, timestamp=instance.timestamp
            ).first()

            if edit_attendance:
                edit_attendance.status = "approved"
                edit_attendance.save()

                instance.edit_time_attendance = edit_attendance
                instance.save()

    elif instance.status == "rejected":
        if instance.approval_type == "leave":
            # ปฏิเสธคำขอลา
            leave_attendance = LeaveAttendance.objects.filter(
                id=instance.leave_attendance.id
            ).first()

            if leave_attendance:
                leave_attendance.status = "rejected"
                leave_attendance.save()

        elif instance.approval_type == "edit_time":
            edit_attendance = EditTimeAttendance.objects.filter(
                date=instance.date, status="pending", approve_user=instance.approve_user, user=instance.request_user,
                branch=instance.branch, timestamp=instance.timestamp
            ).first()

            if edit_attendance:
                edit_attendance.status = "rejected"
                edit_attendance.save()

                instance.edit_time_attendance = edit_attendance
                instance.save()

    elif instance.status == "cancelled":
        if instance.approval_type == "leave":
            # ปฏิเสธคำขอลา
            leave_attendance = LeaveAttendance.objects.filter(
                id=instance.leave_attendance.id
            ).first()

            if leave_attendance:
                leave_attendance.status = "cancelled"
                leave_attendance.save()

        elif instance.approval_type == "edit_time":
            edit_attendance = EditTimeAttendance.objects.filter(
                date=instance.date, status="pending", approve_user=instance.approve_user, user=instance.request_user,
                branch=instance.branch, timestamp=instance.timestamp
            ).first()

            if edit_attendance:
                edit_attendance.status = "cancelled"
                edit_attendance.save()

                instance.edit_time_attendance = edit_attendance
                instance.save()


