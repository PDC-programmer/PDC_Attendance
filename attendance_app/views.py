from django.shortcuts import render
from django.http import JsonResponse
from user_app.models import User, BsnStaff
from attendance_app.models import LeaveAttendance, LeaveBalance, LeaveType
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from linebot import LineBotApi
from linebot.models import TemplateSendMessage, ButtonsTemplate, PostbackAction, TextSendMessage
from datetime import datetime

# Initialize LineBotApi
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)


def get_leave_types(request):
    # ดึงข้อมูลประเภทการลา
    leave_types = LeaveType.objects.all()
    data = [{"id": leave.id,
             "th_name": leave.th_name,
             "en_name": leave.en_name,
             "description": leave.description
             } for leave in leave_types]
    return JsonResponse(data, safe=False)


def get_leave_balances(request, user_id):
    # ค้นหา User ที่มี UID ตรงกับ userID
    user = User.objects.filter(uid=user_id).first()
    if not user:
        return JsonResponse({"error": "ไม่พบข้อมูผู้ใช้งานในระบบ"}, status=404)

    # ดึงข้อมูลประเภทการลา
    leave_balances = LeaveBalance.objects.filter(user=user)
    data = [{"leave_type": leave.leave_type.th_name,
             "total_days": leave.total_days,
             "remaining_days": leave.remaining_days
             } for leave in leave_balances]
    return JsonResponse(data, safe=False)


def get_staff(request, user_id):
    # ค้นหา User ที่มี UID ตรงกับ userID
    user = User.objects.filter(uid=user_id).first()
    if not user:
        return JsonResponse({"error": "ไม่พบข้อมูผู้ใช้งานในระบบ"}, status=404)

    staff = BsnStaff.objects.filter(django_usr_id=user).first()
    if not staff:
        return JsonResponse({"error": "ไม่พบข้อมูลพนักงาน"}, status=404)
    return JsonResponse({
        "staff_code": staff.staff_code,
        "staff_fname": staff.staff_fname,
        "staff_lname": staff.staff_lname,
        "staff_title": staff.staff_title,
        "staff_department": staff.staff_department,
    }, status=200)


def get_leave_attendances(request, user_id):
    # ค้นหา User ที่มี UID ตรงกับ userID
    user = User.objects.filter(uid=user_id).first()
    if not user:
        return JsonResponse({"error": "ไม่พบข้อมูผู้ใช้งานในระบบ"}, status=404)

    leave_attendances = LeaveAttendance.objects.filter(user=user)
    if not leave_attendances:
        return JsonResponse({"error": "ไม่พบข้อมูลคำขออนุมัติ"}, status=404)

    # ค้นหาข้อมูลผู้อนุมัติใน BsnStaff
    # approver_staff = BsnStaff.objects.filter(django_usr_id=attendance.approve_user).first()

    # หากไม่พบข้อมูลใน BsnStaff ให้แสดงข้อมูลจาก approve_user แทน
    # if approver_staff:
    #     approver_name = f"{approver_staff.staff_fname} {approver_staff.staff_lname}"
    # else:
    #     approver_name = attendance.approve_user.username if attendance.approve_user else "N/A"

    data = [{"id": leave.id,
             "start_date": leave.start_date,
             "end_date": leave.end_date,
             "leave_type": leave.leave_type.th_name,
             "reason": leave.reason,
             "status": leave.status,
             # "image": leave.image,
             } for leave in leave_attendances]
    return JsonResponse(data, safe=False)


@csrf_exempt
def leave_request_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data.get("userID")
        start_date = data.get("startDate")
        end_date = data.get("endDate")
        reason = data.get("reason")
        leave_type_id = data.get("type")

        days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1

        # ตรวจสอบว่าประเภทการลามีอยู่ในระบบ
        leave_type = LeaveType.objects.filter(id=leave_type_id).first()
        if not leave_type:
            return JsonResponse({"error": "ประเภทวันลาไม่ถูกต้อง !"}, status=400)

        # ค้นหา User ที่มี UID ตรงกับ userID
        user = User.objects.filter(uid=user_id).first()
        if not user:
            return JsonResponse({"error": "ไม่พบข้อมูผู้ใช้งานในระบบ !"}, status=404)

        leave_balance = LeaveBalance.objects.filter(user=user, leave_type=leave_type_id).first()
        if not leave_balance:
            return JsonResponse({"error": "ไม่พบข้อมูสิทธิ์วันลาคงเหลือ !"}, status=404)

        if not leave_balance.remaining_days >= days:
            return JsonResponse({"error": f"{leave_type.th_name}เหลือไม่เพียงพอ !"}, status=404)

        # ค้นหาผู้อนุมัติจากตาราง BsnStaff
        staff = BsnStaff.objects.filter(django_usr_id=user).first()
        if not staff or not staff.mng_staff_id:
            return JsonResponse({"error": "ไม่พบผู้อนุมัติของพนักงาน !"}, status=404)

        approver = BsnStaff.objects.filter(staff_id=staff.mng_staff_id).first()
        approver_user = User.objects.filter(id=approver.django_usr_id.id).first()
        if not approver_user:
            return JsonResponse({"error": "ไม่พบผู้อนุมัติ !"}, status=404)

        # สร้าง LeaveAttendance
        leave_record = LeaveAttendance.objects.create(
            user=user,
            approve_user=approver_user,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            leave_type=leave_type,
        )

        # ส่ง Template Message ถึง Approver
        if approver_user.uid:
            user_fullname = f"{staff.staff_fname} {staff.staff_lname}" if staff.staff_fname and staff.staff_lname else user.username
            approver_fullname = f"{approver.staff_fname} {approver.staff_lname}" if approver.staff_fname and approver.staff_lname else approver_user.username

            try:
                line_bot_api.push_message(
                    approver_user.uid,
                    TemplateSendMessage(
                        alt_text=f"คำขอการลาของ {user_fullname}",
                        template=ButtonsTemplate(
                            title=f"คำขอการลาของ {user_fullname}: {leave_record.id}",
                            text=f"ประเภท: {leave_type.th_name}\nวัน: {start_date} - {end_date}\nคงเหลือ: {leave_balance.remaining_days}",
                            actions=[
                                PostbackAction(
                                    label="อนุมัติ",
                                    display_text=f"อนุมัติคำขอการลารหัส: {leave_record.id}",
                                    data=f"action=approve&leave_id={leave_record.id}"
                                ),
                                PostbackAction(
                                    label="ปฏิเสธ",
                                    display_text=f"ปฏิเสธคำขอการลารหัส: {leave_record.id}",
                                    data=f"action=reject&leave_id={leave_record.id}"
                                ),
                            ]
                        )
                    )
                )
            except Exception as e:
                return JsonResponse({"error": f"Failed to send message: {str(e)}"}, status=500)

            if not user:
                return JsonResponse({"error": "ไม่พบข้อมูผู้ใช้งานในระบบ"}, status=404)
            else:
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(
                        text=f"คำขอการลา: {leave_record.id}\nกำลังรอการพิจารณา\nผู้อนุมัติ: {approver_fullname}"
                    )
                )

        return JsonResponse({"message": "Leave request submitted and notification sent successfully"}, status=201)

    return render(request, "attendance/leave_request.html")
