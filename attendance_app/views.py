from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from user_app.models import User, BsnStaff
from attendance_app.models import LeaveAttendance, LeaveBalance, LeaveType
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from linebot import LineBotApi
from linebot.models import TemplateSendMessage, ButtonsTemplate, PostbackAction, TextSendMessage, URIAction
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from attendance_app.utils import calculate_working_hours  # Import the utility function
from django.utils.timezone import now
from django.db.models import Q
from datetime import datetime
from django.utils.dateparse import parse_date

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
    data = [{"leave_type": leave.leave_type.th_name,
             "used_hours": leave.total_hours - leave.remaining_hours,
             "remaining_hours": leave.remaining_hours
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
            start_datetime__lte=start_datetime,
            end_datetime__gte=start_datetime
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

        # Add leave details to the response data
        data.append({
            "id": leave.id,
            "approve_user": approver_name,
            "start_datetime": leave.start_datetime,
            "end_datetime": leave.end_datetime,
            "leave_type": leave.leave_type.th_name,
            "reason": leave.reason,
            "status": leave.get_status_display(),
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
def leave_request_view(request):
    if request.method == "POST":
        # ตรวจสอบการส่งข้อมูลแบบ FormData
        data = request.POST
        image = request.FILES.get("image")

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
            image=image,
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
                            # thumbnail_image_url=leave_record.image.url if leave_record.image else None,
                            # Add image URL here
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

            if not user:
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
                                title=f"คำขอการลาของ {user_fullname}: {leave_record.id}",
                                text=f"ประเภท: {leave_type.th_name}\nวัน: {start_date} - {end_date}\nคงเหลือ: {leave_balance.remaining_days}",
                                actions=[
                                    PostbackAction(
                                        label="ยกเลิก",
                                        display_text=f"ยกเลิกคำขอการลารหัส: {leave_record.id}",
                                        data=f"action=cancel&leave_id={leave_record.id}"
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

    return render(request, "attendance/leave_request.html")


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

        # Calculate working hours only
        working_hours = calculate_working_hours(start_datetime, end_datetime)

        if working_hours <= 0:
            return JsonResponse({"error": "ช่วงเวลาที่เลือกไม่ได้อยู่ในเวลาทำงาน"}, status=400)

        # days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1

        user = SocialAccount.objects.filter(user=request.user).first()
        user_id = user.uid

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

        # สร้าง LeaveAttendance
        leave_record = LeaveAttendance.objects.create(
            user=user.user,
            approve_user=approver_user.user,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
            leave_type=leave_type,
            image=image,
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
                            title=f"คำขอการลาของ {user_fullname}: {leave_record.id}",
                            text=f"{datetime.date(start_datetime).strftime("%d/%m/%y")} - {datetime.date(end_datetime).strftime("%d/%m/%y")}\n{leave_type.th_name}\nเหลือ: {leave_balance.remaining_hours // 8} วัน",
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
                                title=f"คำขอการลาของ {user_fullname}: {leave_record.id}",
                                text=f"{datetime.date(start_datetime).strftime("%d/%m/%y")} - {datetime.date(end_datetime).strftime("%d/%m/%y")}\n{leave_type.th_name}\nเหลือ: {leave_balance.remaining_hours // 8} วัน",
                                actions=[
                                    PostbackAction(
                                        label="ยกเลิก",
                                        display_text=f"ยกเลิกคำขอการลารหัส: {leave_record.id}",
                                        data=f"action=cancel&leave_id={leave_record.id}"
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

    # Calculate working hours only
    total_duration = calculate_working_hours(leave_request.start_datetime, leave_request.end_datetime)
    leave_hours = f"{total_duration // 8:.0f} วัน" if total_duration >= 8 else f"{total_duration:.1f} ชม."
    staff = BsnStaff.objects.filter(django_usr_id=leave_request.user.id).first()
    approver = BsnStaff.objects.filter(django_usr_id=leave_request.approve_user.id).first()

    # Verify that the logged-in user is either the approver or the requester
    if request.user != leave_request.approve_user and request.user != leave_request.user:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์เข้าถึงข้อมูลนี้ !")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "approve" and request.user == leave_request.approve_user:
            if leave_request.status != "approved":
                leave_request.status = "approved"

                # Deduct leave balance
                leave_balance = LeaveBalance.objects.filter(
                    user=leave_request.user, leave_type=leave_request.leave_type
                ).first()

                leave_request.save()
                return JsonResponse({"message": "อนุมัติคำขออนุมัติเสร็จสิ้น"}, status=200)
            else:
                return JsonResponse({"error": "อนุมัติคำขออนุมัติแล้ว"}, status=400)

        elif action == "reject" and request.user == leave_request.approve_user:
            if leave_request.status != "rejected":
                leave_request.status = "rejected"

                # Deduct leave balance
                leave_balance = LeaveBalance.objects.filter(
                    user=leave_request.user, leave_type=leave_request.leave_type
                ).first()

                leave_request.save()
                return JsonResponse({"message": "ปฏิเสธคำขออนุมัติเสร็จสิ้น"}, status=200)
            else:
                return JsonResponse({"error": "ปฏิเสธคำขออนุมัติแล้ว"}, status=400)

        elif action == "cancel" and request.user == leave_request.user:
            if leave_request.start_datetime < now():
                return JsonResponse({"error": "ไม่สามารถยกเลิกคำขออนุมัติที่ผ่านมาแล้วได้ !"}, status=400)

            if leave_request.status in ["pending", "approved"]:
                leave_request.status = "cancelled"
                leave_request.save()
                return JsonResponse({"message": "ยกเลิกคำขออนุมัติเสร็จสิ้น"}, status=200)
            else:
                return JsonResponse({"error": "ไม่สามารถยกเลิกคำขออนุมัตินี้ได้"}, status=400)

        return HttpResponseForbidden("คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้ !")

    return render(request, "attendance/leave_request_detail.html",
                  {"leave_request": leave_request, "staff": staff, "approver": approver, "leave_hours": leave_hours})


@login_required(login_url='log-in')
def leave_requests_approval(request):
    # Determine if the user is an approver
    if not BsnStaff.objects.filter(django_usr_id=request.user, staff_type="manager").exists():
        return JsonResponse({"error": "คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้ได้"}, status=400)

    # Base queryset for approver
    leave_requests = LeaveAttendance.objects.filter(approve_user=request.user).order_by('-start_datetime')

    # Apply filters from query parameters
    status = request.GET.get("status")
    user = request.GET.get("user")
    leave_type = request.GET.get("leave_type")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

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
            leave_requests = leave_requests.filter(end_datetime__date__lte=end_date_obj)

    # Enrich the data for display
    for leave_request in leave_requests:
        leave_hours = calculate_working_hours(leave_request.start_datetime, leave_request.end_datetime)
        leave_request.total_duration = (
            f"{leave_hours // 8:.0f} วัน" if leave_hours >= 8 else f"{leave_hours:.1f} ชม."
        )
        leave_request.staff_brc = BsnStaff.objects.filter(django_usr_id=leave_request.user).first().brc_id.brc_sname

    leave_types = LeaveType.objects.all()

    return render(request, "attendance/leave_requests_approval.html", {
        "leave_requests": leave_requests,
        "role": "approver",
        "leave_types": leave_types,
    })


@login_required(login_url='log-in')
def leave_requests_list(request):
    # Determine if the user is an approver or requester
    if BsnStaff.objects.filter(django_usr_id=request.user).exists():
        leave_requests = LeaveAttendance.objects.filter(user=request.user).order_by('-start_datetime')

        # Apply filters from query parameters
        status = request.GET.get("status")
        leave_type = request.GET.get("leave_type")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

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
                leave_requests = leave_requests.filter(end_datetime__date__lte=end_date_obj)

        for leave_request in leave_requests:
            # Calculate working hours only
            leave_hours = calculate_working_hours(leave_request.start_datetime, leave_request.end_datetime)
            leave_request.total_duration = (
                f"{leave_hours // 8:.0f} วัน" if leave_hours >= 8 else f"{leave_hours:.1f} ชม."
            )
            leave_request.staff_brc = BsnStaff.objects.filter(django_usr_id=leave_request.user).first().brc_id.brc_sname
    else:
        return JsonResponse({"error": "คุณไม่มีสิทธิ์เข้าถึงการดำเนินการนี้ได้"}, status=400)

    leave_types = LeaveType.objects.all()

    return render(request, "attendance/leave_requests_list.html", {
        "leave_requests": leave_requests,
        "leave_types": leave_types,
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
