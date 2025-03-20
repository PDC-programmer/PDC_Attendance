from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.utils import timezone

from user_app.models import User, BsnStaff
from attendance_app.models import *
from approval_app.models import *
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from linebot import LineBotApi
from linebot.models import TemplateSendMessage, ButtonsTemplate, PostbackAction, TextSendMessage, URIAction
from django.contrib.auth.decorators import login_required, user_passes_test
from allauth.socialaccount.models import SocialAccount
from attendance_app.utils import calculate_working_hours  # Import the utility function
from django.utils.timezone import now
from django.db.models import Q
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
import csv
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from django.db import transaction
from django.contrib import messages
import pandas as pd
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.utils.timezone import make_aware
from django.db.models import Min, Max
from geopy.distance import geodesic  # ใช้สำหรับคำนวณระยะทาง
from branch_app.models import BsnBranch

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


@login_required
def get_leave_balances(request):
    # ดึงข้อมูลประเภทการลา
    leave_balances = LeaveBalance.objects.filter(user=request.user)
    data = [{"leave_type_id": leave.id,
             "leave_type": leave.leave_type.th_name,
             "used_hours": leave.total_hours - leave.remaining_hours,
             "remaining_hours": leave.remaining_hours,
             "total_hours": leave.total_hours,
             } for leave in leave_balances]
    return JsonResponse(data, safe=False)


@login_required
def get_staff(request):
    staff = BsnStaff.objects.filter(django_usr_id=request.user).first()
    if not staff:
        return JsonResponse({"error": "ไม่พบข้อมูลพนักงาน"}, status=404)

    # Format date_of_start as dd/mm/yyyy
    date_of_start_formatted = staff.date_of_start.strftime("%d/%m/%Y") if staff.date_of_start else None

    return JsonResponse({
        "staff_code": staff.staff_code,
        "staff_fname": staff.staff_fname,
        "staff_lname": staff.staff_lname,
        "staff_brc": staff.brc_id.brc_sname,
        "staff_title": staff.staff_title,
        "staff_department": staff.staff_department,
        "date_of_start": date_of_start_formatted,
    }, status=200)


@login_required
def get_leave_attendances(request):
    leave_attendances = LeaveAttendance.objects.filter(user=request.user)

    # รับค่า start_date, end_date และ leave_type จาก query parameters

    # start_datetime = datetime.strptime(data.get("start_datetime"), "%Y-%m-%dT%H:%M")
    start_datetime = request.GET.get("start_datetime")
    leave_type_id = request.GET.get("leave_type")

    # กรองข้อมูลตาม start_date, และ leave_type
    if start_datetime:
        leave_attendances = leave_attendances.filter(
            start_datetime__date__lte=start_datetime,
            start_datetime__date__gte=start_datetime
        )
    if leave_type_id:
        leave_attendances = leave_attendances.filter(leave_type_id=leave_type_id)

    if not leave_attendances.exists():
        return JsonResponse({"error": "ไม่พบข้อมูลคำขออนุมัติ"}, status=404)

    data = []
    for leave in leave_attendances:
        # ค้นหาข้อมูลผู้อนุมัติใน BsnStaff
        approver_staff = BsnStaff.objects.filter(
            django_usr_id=leave.approve_user.id).first() if leave.approve_user else None

        # หากไม่พบข้อมูลใน BsnStaff ให้แสดงข้อมูลจาก approve_user แทน
        if approver_staff:
            approver_name = f"{approver_staff.staff_fname} {approver_staff.staff_lname}"
        else:
            approver_name = leave.approve_user.username if leave.approve_user else "N/A"

        approval = Approval.objects.filter(leave_attendance=leave).first()

        # Add leave details to the response data
        data.append({
            "id": leave.id,
            "approval_id": approval.id,
            "approve_user": approver_name,
            "start_datetime": leave.start_datetime,
            "end_datetime": leave.end_datetime,
            "leave_type": leave.leave_type.th_name,
            "reason": leave.reason,
            "status": leave.get_status_display(),
        })

    return JsonResponse(data, safe=False)


@login_required(login_url='log-in')
@csrf_exempt
def leave_request_view_auth(request):
    if request.method == "POST":
        # ตรวจสอบการส่งข้อมูลแบบ FormData
        data = request.POST
        image = request.FILES.get("image")

        start_datetime = datetime.strptime(data.get("start_datetime"), "%Y-%m-%dT%H:%M")
        end_datetime = datetime.strptime(data.get("end_datetime"), "%Y-%m-%dT%H:%M")
        reason = data.get("reason")
        leave_type_id = data.get("type")

        # Retrieve user details
        user = request.user
        social_account = SocialAccount.objects.filter(user=user).first()
        if not social_account:
            return JsonResponse({"error": "ไม่พบข้อมูล Social Account"}, status=404)

        user_id = social_account.uid

        # Calculate working hours based on shifts
        working_hours = calculate_working_hours(user, start_datetime, end_datetime)
        if working_hours <= 0:
            return JsonResponse(
                {"error": "ช่วงเวลาที่เลือกไม่ได้อยู่ในเวลาทำงาน กรุณาเลือกเวลาทำงานของคุณก่อนทำการลา !"}, status=400)

        # ตรวจสอบว่าประเภทการลามีอยู่ในระบบ
        leave_type = LeaveType.objects.filter(id=leave_type_id).first()
        if not leave_type:
            return JsonResponse({"error": "ประเภทวันลาไม่ถูกต้อง !"}, status=400)

        leave_balance = LeaveBalance.objects.filter(user=request.user, leave_type=leave_type_id).first()
        if not leave_balance:
            return JsonResponse({"error": "ไม่พบข้อมูสิทธิ์วันลาคงเหลือ !"}, status=404)

        if not leave_balance.remaining_hours >= working_hours:
            return JsonResponse({"error": f"{leave_type.th_name}เหลือไม่เพียงพอ !"}, status=404)

        # ค้นหาผู้อนุมัติจากตาราง BsnStaff
        staff = BsnStaff.objects.filter(django_usr_id=request.user).first()
        if not staff or not staff.mng_staff_id:
            return JsonResponse({"error": "ไม่พบผู้อนุมัติของพนักงาน !"}, status=404)

        approver = BsnStaff.objects.filter(staff_id=staff.mng_staff_id).first()
        approver_person = User.objects.filter(id=approver.django_usr_id.id).first()
        approver_user = SocialAccount.objects.filter(user=approver_person).first()
        if not approver_user:
            return JsonResponse({"error": "ไม่พบผู้อนุมัติ !"}, status=404)

        created_leave_attendance = LeaveAttendance.objects.filter(user=user, status__in=["pending", "approved"])

        is_already_created = created_leave_attendance.filter(start_datetime__date=start_datetime.date()).exists()

        if is_already_created:
            return JsonResponse({"error": "พบวันลาที่ตรงกับการลาครั้งนี้ !"}, status=404)

        # สร้าง LeaveAttendance
        leave_record = LeaveAttendance.objects.create(
            user=user,
            approve_user=approver_user.user,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
            leave_type=leave_type,
            image=image,
        )

        # สร้าง Approval
        approval_record = Approval.objects.create(
            leave_attendance=leave_record,
            request_user=user,
            approve_user=approver_user.user,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
            leave_type=leave_type,
            image=leave_record.image,
            approval_type="leave",
            status="pending",
            created_at=now()
        )

        # ส่ง Template Message ถึง Approver
        if approver_user.uid:
            user_fullname = f"{staff.staff_fname} {staff.staff_lname}" if staff.staff_fname and staff.staff_lname else request.user.username
            approver_fullname = f"{approver.staff_fname} {approver.staff_lname}" if approver.staff_fname and approver.staff_lname else approver_user.user.username

            try:
                line_bot_api.push_message(
                    approver_user.uid,
                    TemplateSendMessage(
                        alt_text=f"คำขอการลาของ {user_fullname}",
                        template=ButtonsTemplate(
                            # thumbnail_image_url=leave_record.image.url if leave_record.image else None,
                            # Add image URL here
                            title=f"คำขอการลาของ {user_fullname}: {approval_record.id}",
                            text=f"{datetime.date(start_datetime).strftime("%d/%m/%y")} - {datetime.date(end_datetime).strftime("%d/%m/%y")}\n{leave_type.th_name}\nเหลือ: {leave_balance.remaining_hours // 8} วัน",
                            actions=[
                                PostbackAction(
                                    label="อนุมัติ",
                                    display_text=f"อนุมัติคำขอการลารหัส: {approval_record.id}",
                                    data=f"action=approve&approval_id={approval_record.id}&approval_type=leave"
                                ),
                                PostbackAction(
                                    label="ปฏิเสธ",
                                    display_text=f"ปฏิเสธคำขอการลารหัส: {approval_record.id}",
                                    data=f"action=reject&approval_id={approval_record.id}&approval_type=leave"
                                ),
                                URIAction(
                                    label="ดูรายละเอียด",
                                    uri=f"https://plusdentalclinic-attendance-ec6ce5056c43.herokuapp.com/attendance/leave-request-detail/{leave_record.id}/"
                                ),
                            ]
                        )
                    )
                )
            except Exception as e:
                return JsonResponse({"error": f"Failed to send message: {str(e)}"}, status=500)

            if not request.user:
                return JsonResponse({"error": "ไม่พบข้อมูผู้ใช้งานในระบบ"}, status=404)
            else:
                try:
                    line_bot_api.push_message(
                        user_id,
                        TemplateSendMessage(
                            alt_text=f"คำขอการลาของ {user_fullname}",
                            template=ButtonsTemplate(
                                # thumbnail_image_url=leave_record.image.url if leave_record.image else None,
                                # Add image URL here
                                title=f"คำขอการลาของ {user_fullname}: {approval_record.id}",
                                text=f"{datetime.date(start_datetime).strftime("%d/%m/%y")} - {datetime.date(end_datetime).strftime("%d/%m/%y")}\n{leave_type.th_name}\nเหลือ: {leave_balance.remaining_hours // 8} วัน",
                                actions=[
                                    PostbackAction(
                                        label="ยกเลิก",
                                        display_text=f"ยกเลิกคำขอการลารหัส: {approval_record.id}",
                                        data=f"action=cancel&approval_id={approval_record.id}&approval_type=leave"
                                    ),
                                    URIAction(
                                        label="ดูรายละเอียด",
                                        uri=f"https://plusdentalclinic-attendance-ec6ce5056c43.herokuapp.com/attendance/leave-request-detail/{leave_record.id}/"
                                    ),
                                ]
                            )
                        )
                    )
                except Exception as e:
                    return JsonResponse({"error": f"Failed to send message: {str(e)}"}, status=500)
                # line_bot_api.push_message(
                #     user_id,
                #     TextSendMessage(
                #         text=f"คำขอการลา: {leave_record.id}\nกำลังรอการพิจารณา\nผู้อนุมัติ: {approver_fullname}"
                #     )
                # )

        return JsonResponse({"message": "Leave request submitted and notification sent successfully"}, status=201)

    context = {
        "hours_range": range(8, 22),  # ช่วงชั่วโมงตั้งแต่ 8 ถึง 21
    }

    return render(request, "attendance/leave_request_auth.html", context)


@login_required(login_url='log-in')
def leave_request_detail(request, leave_id):
    # Fetch LeaveAttendance object
    leave_request = get_object_or_404(LeaveAttendance, id=leave_id)
    approval = Approval.objects.filter(leave_attendance=leave_request.id).first()

    # Calculate working hours only
    total_duration = calculate_working_hours(approval.request_user, approval.start_datetime, approval.end_datetime)
    leave_hours = f"{total_duration // 8:.0f} วัน" if total_duration >= 8 else f"{total_duration:.1f} ชม."
    staff = BsnStaff.objects.filter(django_usr_id=approval.request_user.id).first()
    approver = BsnStaff.objects.filter(django_usr_id=approval.approve_user.id).first()

    # Verify that the logged-in user is either the approver or the requester
    if request.user != approval.approve_user and request.user != approval.request_user:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์เข้าถึงข้อมูลนี้ !")

    if request.method == "POST":
        action = request.POST.get("action")

        # Deduct leave balance
        leave_balance = LeaveBalance.objects.filter(
            user=approval.request_user, leave_type=approval.leave_type
        ).first()

        if action == "approve" and request.user == approval.approve_user:
            if approval.status != "approved":
                approval.status = "approved"
                approval.updated_at = now()
                approval.save()

                return JsonResponse({"message": "อนุมัติคำขออนุมัติเสร็จสิ้น"}, status=200)
            else:
                return JsonResponse({"error": "อนุมัติคำขออนุมัติแล้ว"}, status=400)

        elif action == "reject" and request.user == approval.approve_user:
            if approval.status != "rejected":
                approval.status = "rejected"
                approval.updated_at = now()
                approval.save()
                return JsonResponse({"message": "ปฏิเสธคำขออนุมัติเสร็จสิ้น"}, status=200)
            else:
                return JsonResponse({"error": "ปฏิเสธคำขออนุมัติแล้ว"}, status=400)

        elif action == "cancel" and request.user == approval.request_user:
            if approval.start_datetime < now():
                return JsonResponse({"error": "ไม่สามารถยกเลิกคำขออนุมัติที่ผ่านมาแล้วได้ !"}, status=400)

            if approval.status in ["pending", "approved"]:
                approval.status = "cancelled"
                approval.updated_at = now()
                approval.save()
                return JsonResponse({"message": "ยกเลิกคำขออนุมัติเสร็จสิ้น"}, status=200)
            else:
                return JsonResponse({"error": "ไม่สามารถยกเลิกคำขออนุมัตินี้ได้"}, status=400)

        return HttpResponseForbidden("คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้ !")

    return render(request, "attendance/leave_request_detail.html",
                  {"leave_request": leave_request, "staff": staff, "approver": approver, "leave_hours": leave_hours,
                   "approval": approval})


from django.utils.dateparse import parse_date


@login_required(login_url='log-in')
def leave_requests_approval(request):
    # ตรวจสอบสิทธิ์ของผู้ใช้
    if not User.objects.filter(username=request.user, groups=3).exists():
        return JsonResponse({"error": "คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้ได้"}, status=400)

    # รับค่าค้นหาจาก query parameters
    status = request.GET.get("status")
    user = request.GET.get("user")
    leave_type = request.GET.get("leave_type")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # ตรวจสอบว่ามีการค้นหาหรือไม่
    is_searching = any([status, user, leave_type, start_date, end_date])

    # ถ้าไม่มีการค้นหา ให้แสดงข้อความ "กรุณาค้นหาคำขออนุมัติ"
    if not is_searching:
        return render(request, "attendance/leave_requests_approval.html", {
            "leave_requests": None,
            "role": "approver",
            "leave_types": LeaveType.objects.all(),
        })

    # Query คำขออนุมัติ
    leave_requests = LeaveAttendance.objects.filter(approve_user=request.user).order_by('-start_datetime')

    if status:
        leave_requests = leave_requests.filter(status=status)

    if user:
        leave_requests = leave_requests.filter(
            Q(user__first_name__icontains=user) | Q(user__last_name__icontains=user)
        )

    if leave_type:
        leave_requests = leave_requests.filter(leave_type__id=leave_type)

    if start_date:
        start_date_obj = parse_date(start_date)
        if start_date_obj:
            leave_requests = leave_requests.filter(start_datetime__date__gte=start_date_obj)

    if end_date:
        end_date_obj = parse_date(end_date)
        if end_date_obj:
            leave_requests = leave_requests.filter(start_datetime__date__lte=end_date_obj)

    # เพิ่มข้อมูลที่คำนวณได้สำหรับการแสดงผล
    for leave_request in leave_requests:
        leave_hours = calculate_working_hours(leave_request.user, leave_request.start_datetime,
                                              leave_request.end_datetime)
        leave_request.total_duration = (
            f"{leave_hours // 8:.0f} วัน" if leave_hours >= 8 else f"{leave_hours:.1f} ชม."
        )
        staff_info = BsnStaff.objects.filter(django_usr_id=leave_request.user).first()
        leave_request.staff_brc = staff_info.brc_id.brc_sname if staff_info else "N/A"

    return render(request, "attendance/leave_requests_approval.html", {
        "leave_requests": leave_requests,
        "role": "approver",
        "leave_types": LeaveType.objects.all(),
    })


@login_required(login_url='log-in')
def leave_requests_list(request):
    # ตรวจสอบว่าผู้ใช้เป็นพนักงานหรือไม่
    if not BsnStaff.objects.filter(django_usr_id=request.user).exists():
        return JsonResponse({"error": "คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้ได้"}, status=400)

    # รับค่าค้นหาจาก query parameters
    status = request.GET.get("status")
    leave_type = request.GET.get("leave_type")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # ตรวจสอบว่ามีการค้นหาหรือไม่
    is_searching = any([status, leave_type, start_date, end_date])

    # ถ้าไม่มีการค้นหา ให้แสดงข้อความ "กรุณาค้นหาคำขออนุมัติ"
    if not is_searching:
        return render(request, "attendance/leave_requests_list.html", {
            "leave_requests": None,
            "leave_types": LeaveType.objects.all(),
        })

    # Query คำขออนุมัติ
    leave_requests = LeaveAttendance.objects.filter(user=request.user).order_by('-start_datetime')

    if status:
        leave_requests = leave_requests.filter(status=status)

    if leave_type:
        leave_requests = leave_requests.filter(leave_type__id=leave_type)

    if start_date:
        start_date_obj = parse_date(start_date)
        if start_date_obj:
            leave_requests = leave_requests.filter(start_datetime__date__gte=start_date_obj)

    if end_date:
        end_date_obj = parse_date(end_date)
        if end_date_obj:
            leave_requests = leave_requests.filter(start_datetime__date__lte=end_date_obj)

    # เพิ่มข้อมูลที่คำนวณได้สำหรับการแสดงผล
    for leave_request in leave_requests:
        leave_hours = calculate_working_hours(leave_request.user, leave_request.start_datetime,
                                              leave_request.end_datetime)
        leave_request.total_duration = (
            f"{leave_hours // 8:.0f} วัน" if leave_hours >= 8 else f"{leave_hours:.1f} ชม."
        )
        staff_info = BsnStaff.objects.filter(django_usr_id=leave_request.user).first()
        leave_request.staff_brc = staff_info.brc_id.brc_sname if staff_info else "N/A"

    return render(request, "attendance/leave_requests_list.html", {
        "leave_requests": leave_requests,
        "leave_types": LeaveType.objects.all(),
    })


@csrf_exempt
@login_required(login_url='log-in')
def batch_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            leave_ids = data.get("leave_ids", [])

            if not leave_ids:
                return JsonResponse({"error": "โปรดเลือกคำขออนุมัติที่ต้องการพิจารณา !"}, status=400)

            leaves = LeaveAttendance.objects.filter(id__in=leave_ids, status='pending')
            if not leaves.exists():
                return JsonResponse({"error": "คำขออนุมัตินี้ถูกพิจารณาไปแล้ว !"}, status=404)

            if action not in ["approve", "reject"]:
                return JsonResponse({"error": "การพิจารณาไม่ถูกต้อง"}, status=400)

            # Iterate and save each leave request
            for leave in leaves:
                leave.status = "approved" if action == "approve" else "rejected"
                leave.save()

            message = (
                "คำขออนุมัติที่เลือกได้รับการอนุมัติแล้ว !"
                if action == "approve"
                else "คำขออนุมัติที่เลือกได้รับการปฏิเสธแล้ว !"
            )
            return JsonResponse({"message": message}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"พบข้อผิดพลาด: {str(e)}"}, status=500)

    return JsonResponse({"error": "การทำงานผิดพลาด"}, status=405)


# ตรวจสอบว่า user มี is_staff เป็น True
def is_staff_check(user):
    return user.is_staff


@login_required(login_url='log-in')
@user_passes_test(is_staff_check)
def leave_attendance_list(request):
    # รับค่าค้นหาและฟิลเตอร์จาก request GET
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # ตรวจสอบว่ามีเงื่อนไขการค้นหาหรือไม่
    is_searching = any([search_query, status_filter, start_date, end_date])

    # ถ้าไม่มีการค้นหา ให้แสดงผลลัพธ์เป็นค่าว่าง
    if not is_searching:
        return render(request, 'attendance/leave_attendance_list.html', {
            'data': None,  # ส่งค่า None ไปยัง template
            'search_query': search_query,
            'status_filter': status_filter,
            'start_date': start_date,
            'end_date': end_date
        })

    # Query เบื้องต้น
    leave_attendances = LeaveAttendance.objects.select_related('user')

    # ถ้ามีการค้นหา
    if search_query:
        leave_attendances = leave_attendances.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(leave_type__th_name__icontains=search_query)
        )

    # ถ้ามีการกรองสถานะ
    if status_filter:
        leave_attendances = leave_attendances.filter(status=status_filter)

    # ถ้ามีการกรองวันที่
    if start_date and end_date:
        leave_attendances = leave_attendances.filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date
        )

    # เตรียมข้อมูลสำหรับ Template
    data = []
    for attendance in leave_attendances:
        total_duration = calculate_working_hours(attendance.user, attendance.start_datetime, attendance.end_datetime)
        leave_hours = f"{total_duration // 8:.0f} วัน" if total_duration >= 8 else f"{total_duration:.1f} ชม."
        bsn_staff = BsnStaff.objects.filter(django_usr_id=attendance.user).first()
        forward_or_backward_days = (attendance.start_datetime - attendance.created_at).days
        n_name = f"{attendance.user.nick_name}" if attendance.user.nick_name is not None else '-'
        data.append({
            'date_range': f"{attendance.start_datetime:%d/%m/%Y} - {attendance.end_datetime:%d/%m/%Y}",
            'staff_code': bsn_staff.staff_code if bsn_staff else 'N/A',
            'full_name': f"{attendance.user.first_name} {attendance.user.last_name}",
            'nickname': n_name,
            'position': bsn_staff.staff_title if bsn_staff else 'N/A',
            'branch': bsn_staff.brc_id.brc_sname if bsn_staff else 'N/A',
            'leave_type': attendance.leave_type.th_name if attendance.leave_type else 'N/A',
            'request_by': f"{attendance.user.first_name} {attendance.user.last_name}",
            'request_date': f"{attendance.created_at:%d/%m/%Y %H:%M} น.",
            'status': attendance.get_status_display(),
            'approved_by': f"{attendance.approve_user.first_name} {attendance.approve_user.last_name}" if attendance.approve_user else 'N/A',
            'updated_at': f"{attendance.updated_at:%d/%m/%Y %H:%M} น." if attendance.updated_at is not None else '-',
            'details': f"{attendance.user.first_name} {attendance.user.last_name} ({n_name}) ยื่นขอ \"{attendance.leave_type.th_name if attendance.leave_type else 'N/A'}\" ขอลางาน ตั้งแต่วันที่ {attendance.start_datetime:%d/%m/%Y %H:%M} ถึงวันที่ {attendance.end_datetime:%d/%m/%Y %H:%M} หมายเหตุ : {attendance.reason}",
            'hours': leave_hours,
            'total_days': leave_hours,
            'amount': '0.00',
            'forward_or_backward': f'ย้อนหลัง {forward_or_backward_days * (-1)} วัน' if attendance.start_datetime < attendance.created_at else f'ล่วงหน้า {forward_or_backward_days} วัน'
        })

    return render(request, 'attendance/leave_attendance_list.html', {
        'data': data,
        'search_query': search_query,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date
    })


@login_required(login_url='log-in')
@user_passes_test(is_staff_check)
def export_leave_attendance_excel(request):
    # รับค่าการค้นหาและฟิลเตอร์จาก request GET
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Query เบื้องต้น
    leave_attendances = LeaveAttendance.objects.select_related('user')

    # ถ้ามีการค้นหา
    if search_query:
        leave_attendances = leave_attendances.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(leave_type__th_name__icontains=search_query)
        )

    # ถ้ามีการกรองสถานะ
    if status_filter:
        leave_attendances = leave_attendances.filter(status=status_filter)

    # ถ้ามีการกรองวันที่
    if start_date and end_date:
        leave_attendances = leave_attendances.filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date
        )

    # สร้าง Workbook และ Sheet
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "รายการลาของพนักงาน"

    # เขียน Header
    headers = [
        'ลำดับ', 'วันที่', 'รหัสพนักงาน', 'ชื่อ-นามสกุล', 'ชื่อเล่น',
        'ตำแหน่ง', 'สำนักงานสาขา', 'ประเภท', 'ขอโดย', 'ขอวันที่',
        'สถานะ', 'ผู้อนุมัติ', 'อัพเดทเมื่อ', 'รายละเอียด', 'ชั่วโมง/วัน',
        'รวมเป็นเงิน', 'ย้อนหลัง/ล่วงหน้า'
    ]
    sheet.append(headers)

    # ดึงข้อมูลและเขียนลงในไฟล์ Excel
    for idx, attendance in enumerate(leave_attendances):
        total_duration = calculate_working_hours(attendance.user, attendance.start_datetime, attendance.end_datetime)
        leave_hours = f"{total_duration // 8:.0f} วัน" if total_duration >= 8 else f"{total_duration:.1f} ชม."
        bsn_staff = BsnStaff.objects.filter(django_usr_id=attendance.user).first()
        date_range = f"{attendance.start_datetime:%d/%m/%Y} - {attendance.end_datetime:%d/%m/%Y}"
        full_name = f"{attendance.user.first_name} {attendance.user.last_name}"
        n_name = f"{attendance.user.nick_name}" if attendance.user.nick_name is not None else '-'
        details = f"{full_name} ({n_name}) ยื่นขอ \"{attendance.leave_type.th_name if attendance.leave_type else 'N/A'}\" ขอลางาน ตั้งแต่วันที่ {attendance.start_datetime:%d/%m/%Y %H:%M} ถึงวันที่ {attendance.end_datetime:%d/%m/%Y %H:%M} หมายเหตุ : {attendance.reason}"
        forward_or_backward_days = (attendance.start_datetime - attendance.created_at).days
        # เขียนข้อมูลในแต่ละแถว
        sheet.append([
            idx + 1,
            date_range,
            bsn_staff.staff_code if bsn_staff else 'N/A',
            full_name,
            n_name,
            bsn_staff.staff_title if bsn_staff else 'N/A',
            bsn_staff.brc_id.brc_sname if bsn_staff else 'N/A',
            attendance.leave_type.th_name if attendance.leave_type else 'N/A',
            full_name,
            f"{attendance.created_at:%d/%m/%Y %H:%M} น.",
            attendance.get_status_display(),
            f"{attendance.approve_user.first_name} {attendance.approve_user.last_name}" if attendance.approve_user else 'N/A',
            f"{attendance.updated_at:%d/%m/%Y %H:%M} น." if attendance.updated_at is not None else '-',
            details,
            leave_hours,
            '0.00',
            f'ย้อนหลัง {forward_or_backward_days * (-1)} วัน' if attendance.start_datetime < attendance.created_at else f'ล่วงหน้า {forward_or_backward_days} วัน'
        ])

    # กำหนด Response สำหรับการดาวน์โหลดไฟล์
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=leave_attendance_report_{now()}.xlsx'

    # บันทึกไฟล์ Excel ลงใน Response
    workbook.save(response)
    return response


@login_required(login_url='log-in')
def shift_schedule_update(request):
    if request.method == "POST":
        selected_month = int(request.POST.get("month"))
        selected_year = int(request.POST.get("year"))
        selected_shift_id = request.POST.get("shift")

        user = request.user
        staff = BsnStaff.objects.filter(django_usr_id=user).first()
        approver_person = BsnStaff.objects.filter(staff_id=staff.mng_staff_id).first()
        approver_user = User.objects.filter(id=approver_person.django_usr_id.id).first()
        if not approver_user:
            return JsonResponse({"error": "ไม่พบข้อมูลผู้อนุมัติของคุณ !"}, status=400)

        selected_shift = Shift.objects.get(id=selected_shift_id)

        start_date = datetime(selected_year, selected_month, 21).date()
        next_month = selected_month + 1 if selected_month < 12 else 1
        next_year = selected_year if selected_month < 12 else selected_year + 1
        end_date = datetime(next_year, next_month, 20).date()

        already_created_shift_schedule = ShiftSchedule.objects.filter(user=user, date=start_date).exists()

        if already_created_shift_schedule:
            return JsonResponse({"error": "ไม่สามารถดำเนินการได้ มีช่วงเวลาทำงานที่คุณเลือกอยู่แล้ว !"}, status=400)

        is_regular_employee = user.groups.filter(id=1).exists()
        public_holiday_cn = set(PublicHoliday.objects.filter(group="CN").values_list("date", flat=True))
        public_holiday_op = set(PublicHoliday.objects.filter(group="OP").values_list("date", flat=True))

        # existing_schedules = {
        #     (s.date, s.shift_day): s for s in ShiftSchedule.objects.filter(user=user, date__range=[start_date, end_date])
        # }

        shift_schedules_to_create = []
        # shift_schedules_to_update = []

        current_date = start_date
        while current_date <= end_date:
            shift_day = "working_day"

            if is_regular_employee:
                if current_date in public_holiday_cn:
                    shift_day = "public_holiday"
                if current_date.weekday() in [5, 6]:
                    shift_day = "day_off"
            else:
                if current_date in public_holiday_op:
                    shift_day = "public_holiday"

            # if (current_date, shift_day) in existing_schedules:
            #     schedule = existing_schedules[(current_date, shift_day)]
            #     schedule.shift = selected_shift
            #     schedule.status = "approved"
            #     schedule.approve_user = approver_user
            #     shift_schedules_to_update.append(schedule)
            # else:
            shift_schedules_to_create.append(ShiftSchedule(
                user=user,
                date=current_date,
                shift_day=shift_day,
                shift=selected_shift,
                status="approved"
            ))

            current_date += timedelta(days=1)

        with transaction.atomic():
            if shift_schedules_to_create:
                ShiftSchedule.objects.bulk_create(shift_schedules_to_create, ignore_conflicts=True)
            # if shift_schedules_to_update:
            #     ShiftSchedule.objects.bulk_update(shift_schedules_to_update, ['shift', 'status', 'approve_user'])

        return JsonResponse({"message": "อัปเดตตารางกะสำเร็จแล้ว"}, status=200)

    shifts = Shift.objects.all()
    return render(request, "attendance/shift_schedule_update.html", {
        "shifts": shifts,
        "months": range(1, 13),
        "years": range(2025, 2027),
    })


@login_required(login_url='log-in')
def shift_schedule_view(request):
    shifts = Shift.objects.all()

    # ดึงข้อมูลวันลาทั้งหมดที่ได้รับการอนุมัติ
    leave_attendances = LeaveAttendance.objects.filter(user=request.user, status="approved")

    # เก็บช่วงวันที่ทั้งหมดที่อยู่ในช่วงลา
    leave_dates_set = set()
    for leave in leave_attendances:
        current_date = leave.start_datetime.date()
        end_date = leave.end_datetime.date()
        while current_date <= end_date:
            leave_dates_set.add(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

    leave_dates_list = list(leave_dates_set)  # แปลงเป็นลิสต์เพื่อให้ JavaScript ใช้ได้

    if request.method == "GET" and "month" in request.GET and "year" in request.GET:
        selected_month = int(request.GET.get("month"))
        selected_year = int(request.GET.get("year"))

        start_date = datetime(selected_year, selected_month, 21).date()
        next_month = selected_month + 1 if selected_month < 12 else 1
        next_year = selected_year if selected_month < 12 else selected_year + 1
        end_date = datetime(next_year, next_month, 20).date()

        shift_schedules = ShiftSchedule.objects.filter(
            user=request.user, date__range=[start_date, end_date]
        ).order_by("date")

        return render(request, "attendance/shift_schedule_view.html", {
            "shifts": shifts,
            "shift_schedules": shift_schedules,
            "selected_month": selected_month,
            "selected_year": selected_year,
            "months": range(1, 13),
            "years": range(2025, 2027),
            "leave_dates": leave_dates_list,  # ส่งช่วงวันลาไปยัง JavaScript
        })

    return render(request, "attendance/shift_schedule_view.html", {
        "shifts": shifts,
        "months": range(1, 13),
        "years": range(2025, 2027),
    })


@login_required(login_url='log-in')
def shift_schedule_bulk_update(request):
    if request.method == "POST":
        data = json.loads(request.body)
        updates = data.get("updates", {})
        user = request.user
        staff = BsnStaff.objects.filter(django_usr_id=user).first()
        approver_person = BsnStaff.objects.filter(staff_id=staff.mng_staff_id).first()
        approver_user = User.objects.filter(id=approver_person.django_usr_id.id).first()

        for schedule_id, update in updates.items():
            # ดึง instance ของ ShiftSchedule
            shift_schedule_instance = ShiftSchedule.objects.filter(id=schedule_id).first()
            if not shift_schedule_instance:
                continue  # ถ้าไม่พบ shift schedule ให้ข้ามไป

            approval = Approval.objects.create(
                shift_schedule=shift_schedule_instance,  # ใช้ instance แทนค่า ID
                request_user=user,
                approve_user=approver_user,
                approval_type="shift",
                shift_id=update["shift"],  # ใช้ shift_id ที่ถูกต้อง
                date=shift_schedule_instance.date,
                shift_day=update["shift_day"],
                status="pending",
                created_at=timezone.now()
            )

        return JsonResponse({"message": "ส่งคำขอแก้ไขกะสำเร็จแล้ว"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required(login_url='log-in')
def shift_schedule_approve(request):
    if not User.objects.filter(username=request.user, groups=3).exists():
        return JsonResponse({"error": "คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้"}, status=400)

    if request.method == "POST":
        data = json.loads(request.body)
        schedule_id = data.get("schedule_id")
        action = data.get("action")  # "approve" or "reject"

        shift_schedule = get_object_or_404(ShiftSchedule, id=schedule_id)

        if shift_schedule.status != "pending":
            return JsonResponse({"error": "ไม่สามารถอนุมัติคำขอที่ได้รับการพิจารณาแล้วได้"}, status=400)

        if action == "approve":
            shift_schedule.status = "approved"
        elif action == "reject":
            shift_schedule.status = "rejected"
        else:
            return JsonResponse({"error": "การดำเนินการไม่ถูกต้อง"}, status=400)

        shift_schedule.approve_user = request.user
        shift_schedule.updated_at = timezone.now()
        shift_schedule.save()

        return JsonResponse({"message": "อัปเดตสถานะสำเร็จแล้ว"}, status=200)

    # รับค่าค้นหาและตัวกรองจาก request GET
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    # ตรวจสอบว่ามีการค้นหาหรือไม่
    is_searching = any([search_query, status_filter, start_date, end_date])

    # ถ้าไม่มีการค้นหา ให้ schedules เป็น None เพื่อไม่ให้แสดงผลลัพธ์
    if not is_searching:
        return render(request, "attendance/shift_schedule_approve.html", {
            "schedules": None,  # ไม่แสดงตาราง
            "search_query": search_query,
            "status_filter": status_filter,
            "start_date": start_date,
            "end_date": end_date
        })

    # ดึงข้อมูลคำขอที่รออนุมัติ
    schedules = ShiftSchedule.objects.filter(approve_user=request.user).select_related("user", "shift").order_by("date")

    # ค้นหาชื่อพนักงาน
    if search_query:
        schedules = schedules.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # กรองสถานะ
    if status_filter:
        schedules = schedules.filter(status=status_filter)

    # กรองวันที่
    if start_date and end_date:
        schedules = schedules.filter(date__range=[start_date, end_date])

    return render(request, "attendance/shift_schedule_approve.html", {
        "schedules": schedules,
        "search_query": search_query,
        "status_filter": status_filter,
        "start_date": start_date,
        "end_date": end_date
    })


@login_required(login_url='log-in')
def shift_schedule_batch_approve(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            schedule_ids = data.get("schedule_ids", [])
            action = data.get("action")

            if not schedule_ids:
                return JsonResponse({"error": "กรุณาเลือกคำขอที่ต้องการพิจารณา"}, status=400)

            if action not in ["approve", "reject"]:
                return JsonResponse({"error": "การดำเนินการไม่ถูกต้อง"}, status=400)

            # ดึงรายการที่เลือกและเปลี่ยนสถานะ
            schedules = ShiftSchedule.objects.filter(id__in=schedule_ids, status="pending")

            if not schedules.exists():
                return JsonResponse({"error": "ไม่มีคำขอที่สามารถพิจารณาได้"}, status=404)

            update_status = "approved" if action == "approve" else "rejected"

            schedules.update(status=update_status, approve_user=request.user, updated_at=timezone.now())

            return JsonResponse({"message": "อัปเดตสถานะสำเร็จแล้ว"}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"เกิดข้อผิดพลาด: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required(login_url="log-in")
@user_passes_test(is_staff_check)
def leave_balance_list(request):
    search_query = request.GET.get("search", "").strip()
    leave_balances = None  # ตั้งค่าเริ่มต้นเป็น None

    if search_query:
        leave_balances = LeaveBalance.objects.filter(
            user__first_name__icontains=search_query
        ) | LeaveBalance.objects.filter(
            user__last_name__icontains=search_query
        ) | LeaveBalance.objects.filter(
            user__username__icontains=search_query
        )

    return render(request, "attendance/leave_balance_list.html", {
        "leave_balances": leave_balances,
        "search_query": search_query,
    })


@login_required(login_url="log-in")
@user_passes_test(is_staff_check)
def edit_leave_balance(request, leave_balance_id):
    """ ฟังก์ชันแก้ไข Leave Balance """
    leave_balance = get_object_or_404(LeaveBalance, id=leave_balance_id)

    if request.method == "POST":
        total_hours = request.POST.get("total_hours")
        remaining_hours = request.POST.get("remaining_hours")

        try:
            leave_balance.total_hours = float(total_hours)
            leave_balance.remaining_hours = float(remaining_hours)
            leave_balance.save()
            messages.success(request, "อัปเดต Leave Balance สำเร็จ!")
            return redirect("leave_balance_list")
        except ValueError:
            messages.error(request, "กรุณากรอกค่าที่ถูกต้อง")

    return render(request, "attendance/edit_leave_balance.html", {
        "leave_balance": leave_balance
    })


@login_required(login_url="log-in")
@user_passes_test(is_staff_check)
def import_leave_balance(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        file_path = default_storage.save("temp/" + excel_file.name, excel_file)

        try:
            df = pd.read_excel(f"media/{file_path}", engine="openpyxl")

            required_columns = {"username", "leave_type", "total_hours", "remaining_hours"}
            if not required_columns.issubset(df.columns):
                messages.error(request,
                               "❌ ไฟล์ Excel ต้องมีคอลัมน์: username, leave_type, total_hours, remaining_hours")
                print("❌ Missing required columns!")
                return redirect("leave_balance_list")

            imported_count = 0
            for _, row in df.iterrows():
                username = str(row["username"]).strip().zfill(5)
                leave_type_name = str(row["leave_type"]).strip()
                total_hours = float(row["total_hours"])
                remaining_hours = float(row["remaining_hours"])

                user = User.objects.filter(username=username).first()
                if not user:
                    messages.warning(request, f"⚠️ ไม่พบผู้ใช้ {username}, ข้ามข้อมูลนี้")
                    print(f"⚠️ ไม่พบผู้ใช้ {username}")
                    continue

                leave_type = LeaveType.objects.filter(th_name=leave_type_name).first()
                if not leave_type:
                    messages.warning(request, f"⚠️ ไม่พบประเภทการลา {leave_type_name}, ข้ามข้อมูลนี้")
                    print(f"⚠️ ไม่พบประเภทการลา {leave_type_name}")
                    continue

                leave_balance, created = LeaveBalance.objects.update_or_create(
                    user=user,
                    leave_type=leave_type,
                    defaults={
                        "total_hours": total_hours,
                        "remaining_hours": remaining_hours,
                        "updated_at": datetime.now(),
                    }
                )
                imported_count += 1
                print(f"✅ อัปเดต Leave Balance สำเร็จ: {username} - {leave_type_name}")

            messages.success(request, f"✅ นำเข้าและอัปเดต Leave Balance สำเร็จ {imported_count} รายการ")
            print(f"✅ สำเร็จ {imported_count} รายการ")
        except Exception as e:
            messages.error(request, f"❌ เกิดข้อผิดพลาด: {str(e)}")
            print(f"❌ Error: {str(e)}")

        finally:
            # ✅ ลบไฟล์ออกจากเซิร์ฟเวอร์หลังใช้งาน
            if default_storage.exists(file_path):
                default_storage.delete(file_path)

        return redirect("leave_balance_list")

    return redirect("leave_balance_list")


@login_required(login_url="log-in")
def search_attendance(request):
    """ พนักงานสามารถค้นหาประวัติการเข้าออกงานของตนเองได้ """
    search_date = request.GET.get("date", "")

    # ดึงข้อมูลจาก TaLog ที่เกี่ยวข้องกับ user ปัจจุบัน
    attendance_logs = TaLog.objects.filter(staff_id=request.user.id).order_by("-log_timestamp")

    # ถ้ากรอกวันที่ ให้กรองเฉพาะวันนั้น
    if search_date:
        attendance_logs = attendance_logs.filter(log_timestamp__date=search_date)

    # ✅ Pagination
    paginator = Paginator(attendance_logs, 10)  # แสดง 10 รายการต่อหน้า
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "attendance/search_attendance.html", {
        "attendance_logs": page_obj,
        "search_date": search_date
    })


@login_required(login_url="log-in")
def search_attendance(request):
    user = request.user
    staff = BsnStaff.objects.filter(django_usr_id=user).first()

    if not staff:
        return render(request, "attendance/search_attendance.html", {
            "error": "ไม่พบข้อมูลพนักงานของคุณ"
        })

    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    attendance_logs = TaLog.objects.filter(staff_id=staff.staff_id)

    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            attendance_logs = attendance_logs.filter(
                log_timestamp__date__range=[start_date, end_date]
            )
        except ValueError:
            return render(request, "attendance/search_attendance.html", {
                "error": "รูปแบบวันที่ไม่ถูกต้อง กรุณาเลือกใหม่"
            })

    attendance_logs = attendance_logs.order_by("-log_timestamp")

    # ✅ Pagination
    paginator = Paginator(attendance_logs, 30)  # แสดง 30 รายการต่อหน้า
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "attendance/search_attendance.html", {
        "attendance_logs": page_obj,
        "start_date": start_date.strftime("%Y-%m-%d") if start_date else "",
        "end_date": end_date.strftime("%Y-%m-%d") if end_date else "",
    })


def find_nearest_branch(lat, lng):
    """ ค้นหาสาขาที่ใกล้ที่สุดจาก GPS """
    try:
        branches = BsnBranch.objects.all().values("id", "brc_sname", "gps_lat", "gps_lng")
        min_distance = float("inf")
        nearest_branch = None

        for branch in branches:
            branch_lat = float(branch["gps_lat"])
            branch_lng = float(branch["gps_lng"])
            distance = geodesic((lat, lng), (branch_lat, branch_lng)).meters  # คำนวณระยะทางเป็นเมตร

            if distance < min_distance:
                min_distance = distance
                nearest_branch = branch["brc_sname"]  # ใช้ชื่อสาขาแทน

        return nearest_branch if nearest_branch else "ไม่พบสาขา"

    except Exception as e:
        print(f"❌ Error finding nearest branch: {e}")
        return "ไม่พบสาขา"


@login_required(login_url="log-in")
def employee_attendance_history(request):
    user = request.user
    staff = BsnStaff.objects.filter(django_usr_id=user).first()
    branches = BsnBranch.objects.all()

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    records = []
    page_obj = None

    if start_date and end_date:
        try:
            start_date = parse_date(start_date)
            end_date = parse_date(end_date)

            if not (start_date and end_date):
                raise ValueError("Invalid date format")

            # ✅ โหลดข้อมูลกะทำงานของพนักงาน
            attendance_records = ShiftSchedule.objects.filter(
                user=user, status="approved", date__range=[start_date, end_date]
            ).select_related("shift").order_by("-date")

            # ✅ โหลดข้อมูลการลาที่ได้รับอนุมัติของพนักงาน
            leave_records = LeaveAttendance.objects.filter(
                user=user, status="approved",
                start_datetime__date__lte=end_date,
                end_datetime__date__gte=start_date
            ).select_related("leave_type")

            # ✅ โหลดข้อมูลแก้ไขเวลา (EditTimeAttendance)
            edit_logs = EditTimeAttendance.objects.filter(
                user=user, date__range=[start_date, end_date], status__in=["pending", "approved"]
            ).values("date", "timestamp", "branch_id")

            # ✅ โหลดข้อมูลบันทึกเวลาเข้าออก (TaLog)
            ta_logs = TaLog.objects.filter(
                staff_id=staff.staff_id, log_timestamp__date__range=[start_date, end_date]
            ).values("log_timestamp", "staff_id", "gps_lat", "gps_lng", "log_timestamp__date")

            # ✅ แมป EditTimeAttendance
            edit_time_map = {}
            for log in edit_logs:
                date_str = log["date"].strftime("%Y-%m-%d")

                if date_str not in edit_time_map:
                    edit_time_map[date_str] = {
                        "check_in": None,
                        "check_out": None,
                        "branch_in": None,
                        "branch_out": None,
                    }

                if not edit_time_map[date_str]["check_in"] or log["timestamp"] < edit_time_map[date_str]["check_in"]:
                    edit_time_map[date_str]["check_in"] = log["timestamp"]
                    edit_time_map[date_str]["branch_in"] = log["branch_id"]

                if not edit_time_map[date_str]["check_out"] or log["timestamp"] > edit_time_map[date_str]["check_out"]:
                    edit_time_map[date_str]["check_out"] = log["timestamp"]
                    edit_time_map[date_str]["branch_out"] = log["branch_id"]

            # ✅ แมป TaLog
            ta_log_map = {}
            for log in ta_logs:
                date_str = log["log_timestamp__date"].strftime("%Y-%m-%d")
                timestamp = log["log_timestamp"]
                lat = log["gps_lat"]
                lng = log["gps_lng"]

                if date_str not in ta_log_map:
                    ta_log_map[date_str] = {
                        "timestamps": [],
                        "check_in": None,
                        "check_out": None,
                        "branch_in": "ไม่พบสาขา",
                        "branch_out": "ไม่พบสาขา",
                    }

                ta_log_map[date_str]["timestamps"].append(timestamp)

            # ✅ แมปวันลาไปยัง records
            leave_map = {}
            for leave in leave_records:
                leave_dates = [leave.start_datetime.date() + timedelta(days=i) for i in
                               range((leave.end_datetime.date() - leave.start_datetime.date()).days + 1)]
                for leave_date in leave_dates:
                    leave_map[leave_date.strftime("%Y-%m-%d")] = {
                        "leave_type": leave.leave_type.th_name,
                        "reason": leave.reason,
                    }

            # ✅ ตรวจสอบข้อมูลเข้า-ออก และเพิ่มวันลา
            for record in attendance_records:
                date_str = record.date.strftime("%Y-%m-%d")
                leave_info = leave_map.get(date_str, None)  # เช็คว่ามีการลาหรือไม่

                if date_str in edit_time_map:  # ✅ ใช้ EditTimeAttendance ถ้ามี
                    log_data = edit_time_map[date_str]
                    branch_in = BsnBranch.objects.filter(id=log_data["branch_in"]).first()
                    branch_out = BsnBranch.objects.filter(id=log_data["branch_out"]).first()

                    records.append({
                        "date": record.date,
                        "shift_day": record.get_shift_day_display(),
                        "shift_name": record.shift.name,
                        "check_in": log_data["check_in"],
                        "check_out": log_data["check_out"],
                        "branch_in": branch_in.brc_sname if branch_in else "ไม่พบสาขา",
                        "branch_out": branch_out.brc_sname if branch_out else "ไม่พบสาขา",
                        "leave_type": leave_info["leave_type"] if leave_info else None,
                        "leave_reason": leave_info["reason"] if leave_info else None,
                    })
                else:  # ✅ ใช้ TaLog ถ้าไม่มี EditTimeAttendance
                    log_data = ta_log_map.get(date_str, {})
                    timestamps = sorted(log_data.get("timestamps", []))
                    shift = record.shift

                    if len(timestamps) == 1:
                        single_log = timestamps[0]
                        shift_midpoint = datetime.combine(record.date, shift.morning_end)

                        if single_log < shift_midpoint:
                            log_data["check_in"] = single_log
                            log_data["branch_in"] = find_nearest_branch(float(lat),
                                                                        float(lng)) if lat and lng else "ไม่พบสาขา"
                        else:
                            log_data["check_out"] = single_log
                            log_data["branch_out"] = find_nearest_branch(float(lat),
                                                                         float(lng)) if lat and lng else "ไม่พบสาขา"

                    elif len(timestamps) > 1:
                        log_data["check_in"] = timestamps[0]
                        log_data["check_out"] = timestamps[-1]
                        log_data["branch_in"] = find_nearest_branch(float(lat),
                                                                    float(lng)) if lat and lng else "ไม่พบสาขา"
                        log_data["branch_out"] = find_nearest_branch(float(lat),
                                                                     float(lng)) if lat and lng else "ไม่พบสาขา"

                    records.append({
                        "date": record.date,
                        "shift_day": record.get_shift_day_display(),
                        "shift_name": record.shift.name,
                        "check_in": log_data.get("check_in"),
                        "check_out": log_data.get("check_out"),
                        "branch_in": log_data.get("branch_in"),
                        "branch_out": log_data.get("branch_out"),
                        "leave_type": leave_info["leave_type"] if leave_info else None,
                        "leave_reason": leave_info["reason"] if leave_info else None,
                    })

            # ✅ Pagination (30 รายการต่อหน้า)
            paginator = Paginator(records, 30)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

        except ValueError:
            return render(request, "attendance/attendance_history.html", {
                "error": "รูปแบบวันที่ไม่ถูกต้อง กรุณาเลือกใหม่"
            })

    return render(request, "attendance/attendance_history.html", {
        "records": page_obj,
        "start_date": start_date.strftime("%Y-%m-%d") if start_date else "",
        "end_date": end_date.strftime("%Y-%m-%d") if end_date else "",
        "branches": branches,
        "hours": range(0, 24),
        "minutes": range(0, 60),
    })


@login_required(login_url="log-in")
@csrf_exempt
def request_edit_time(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            entries = data.get("entries", [])

            if not entries:
                return JsonResponse({"success": False, "error": "ไม่มีข้อมูลที่ต้องบันทึก"}, status=400)

            user = request.user
            staff = BsnStaff.objects.filter(django_usr_id=user).first()

            if not staff:
                return JsonResponse({"success": False, "error": "ไม่พบข้อมูลพนักงาน"}, status=400)

            approver = BsnStaff.objects.filter(staff_id=staff.mng_staff_id).first()
            if not approver:
                return JsonResponse({"success": False, "error": "ไม่พบผู้อนุมัติ"}, status=400)

            approver_user = approver.django_usr_id

            edit_time_entries = []
            approval_entries = []

            for entry in entries:
                date = entry.get("date")
                branch_in = entry.get("branch_in")
                check_in = entry.get("check_in")
                branch_out = entry.get("branch_out")
                check_out = entry.get("check_out")

                # ✅ ตรวจสอบว่าข้อมูลเปลี่ยนแปลงหรือไม่
                existing_in = EditTimeAttendance.objects.filter(
                    user=user, date=date, branch_id=branch_in, timestamp=check_in, status__in=["pending", "approved"]
                ).exists()

                existing_out = EditTimeAttendance.objects.filter(
                    user=user, date=date, branch_id=branch_out, timestamp=check_out, status__in=["pending", "approved"]
                ).exists()

                if not existing_in:
                    edit_time_entries.append(
                        EditTimeAttendance(
                            user=user,
                            approve_user=approver_user,
                            date=date,
                            branch_id=branch_in,
                            timestamp=check_in,
                            status="pending"
                        )
                    )

                    approval_entries.append(
                        Approval(
                            request_user=user,
                            approve_user=approver_user,
                            approval_type="edit_time",
                            date=date,
                            branch_id=branch_in,
                            timestamp=check_in,
                            status="pending"
                        )
                    )

                if not existing_out:
                    edit_time_entries.append(
                        EditTimeAttendance(
                            user=user,
                            approve_user=approver_user,
                            date=date,
                            branch_id=branch_out,
                            timestamp=check_out,
                            status="pending"
                        )
                    )

                    approval_entries.append(
                        Approval(
                            request_user=user,
                            approve_user=approver_user,
                            approval_type="edit_time",
                            date=date,
                            branch_id=branch_out,
                            timestamp=check_out,
                            status="pending"
                        )
                    )

            # ✅ บันทึกเฉพาะรายการที่มีการเปลี่ยนแปลง
            if edit_time_entries:
                EditTimeAttendance.objects.bulk_create(edit_time_entries)
            if approval_entries:
                Approval.objects.bulk_create(approval_entries)

            return JsonResponse({"success": True})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "JSON ไม่ถูกต้อง"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "วิธีการร้องขอไม่ถูกต้อง"}, status=405)
