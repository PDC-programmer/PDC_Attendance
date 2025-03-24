from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from .models import Approval
from attendance_app.models import LeaveAttendance, ShiftSchedule, EditTimeAttendance, LeaveBalance
from django.shortcuts import render
import json
from attendance_app.utils import calculate_working_hours  # Import the utility function
from django.core.paginator import Paginator
from django.db import transaction
from user_app.models import BsnBranch, User
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse


@login_required(login_url='log-in')
def approve_request(request, approval_id, action):
    """
    อนุมัติหรือปฏิเสธคำขอการลา (LeaveAttendance) หรือ เปลี่ยนกะ (ShiftSchedule)
    """
    user = request.user
    if not User.objects.filter(username=request.user, groups=3).exists():
        return HttpResponseForbidden("คุณไม่ใช่ผู้อนุมัติ ไม่มีสิทธิ์อนุมัติได้ !")

    approval = get_object_or_404(Approval, id=approval_id)

    if action not in ["approved", "rejected"]:
        return JsonResponse({"error": "Invalid action"}, status=400)

    # กำหนดสถานะเป็น อนุมัติ หรือ ปฏิเสธ
    approval.status = action
    approval.updated_at = now()
    approval.save()

    messages.success(request, f"พิจารณาคำขอ {approval.get_approval_type_display()} {action} สำเร็จ")
    return redirect("approval_list")  # กลับไปหน้ารายการคำขอ


@login_required(login_url='log-in')
def approval_list(request):
    user = request.user
    if not User.objects.filter(username=request.user, groups=3).exists():
        return HttpResponseForbidden("คุณไม่ใช่ผู้อนุมัติ ไม่มีสิทธิ์เข้าถึงข้อมูลนี้ !")
    search_query = request.GET.get("search", "").strip()
    approval_type_filter = request.GET.get("approval_type", "")
    status = request.GET.get("status", "")

    approvals = Approval.objects.filter(approve_user=request.user)

    if search_query:
        approvals = approvals.filter(
            request_user__first_name__icontains=search_query
        ) | approvals.filter(
            request_user__last_name__icontains=search_query
        ) | approvals.filter(
            request_user__username__icontains=search_query
        )

    if approval_type_filter:
        approvals = approvals.filter(approval_type=approval_type_filter)

    if status:
        approvals = approvals.filter(status=status)

    approvals = approvals.order_by("-created_at")  # เรียงจากใหม่ไปเก่า

    # ✅ Pagination
    paginator = Paginator(approvals, 30)  # แสดง 30 รายการต่อหน้า
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "approval_app/approval_list.html", {
        "approvals": page_obj,
        "search_query": search_query,
        "approval_type_filter": approval_type_filter,
        "status": status,
    })


@login_required(login_url='log-in')
def approval_list_request_user(request):
    search_query = request.GET.get("search", "").strip()
    approval_type_filter = request.GET.get("approval_type", "")
    status = request.GET.get("status", "")

    approvals = Approval.objects.filter(request_user=request.user)

    if search_query:
        approvals = approvals.filter(
            request_user__first_name__icontains=search_query
        ) | approvals.filter(
            request_user__last_name__icontains=search_query
        ) | approvals.filter(
            request_user__username__icontains=search_query
        )

    if approval_type_filter:
        approvals = approvals.filter(approval_type=approval_type_filter)

    if status:
        approvals = approvals.filter(status=status)

    approvals = approvals.order_by("-created_at")  # เรียงจากใหม่ไปเก่า

    # ✅ Pagination
    paginator = Paginator(approvals, 30)  # แสดง 30 รายการต่อหน้า
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "approval_app/approval_list_reqeust_user.html", {
        "approvals": page_obj,
        "search_query": search_query,
        "approval_type_filter": approval_type_filter,
        "status": status,
    })


@login_required(login_url="log-in")
def bulk_approve_requests(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)
    approval_ids = data.get("approval_ids", [])
    action = data.get("action")

    if action not in ["approved", "rejected"]:
        return JsonResponse({"error": "Invalid action"}, status=400)

    approvals = Approval.objects.select_related(
        "leave_attendance", "shift_schedule", "edit_time_attendance"
    ).filter(id__in=approval_ids, status="pending")

    current_time = now()

    approvals_to_update = []
    leave_attendance_to_update = []
    shift_schedule_to_update = []
    edit_time_to_update = []

    with transaction.atomic():
        for approval in approvals:
            approval.status = action
            approval.updated_at = current_time
            approvals_to_update.append(approval)

            # 🛠️ ดำเนินการตาม approval_type
            if approval.approval_type == "leave" and approval.leave_attendance:
                approval.leave_attendance.status = action
                approval.leave_attendance.updated_at = current_time
                leave_attendance_to_update.append(approval.leave_attendance)

            elif approval.approval_type == "shift" and approval.shift_schedule:
                if action == "approved":
                    ss = approval.shift_schedule
                    ss.shift = approval.shift
                    ss.shift_day = approval.shift_day
                    ss.approve_user = approval.approve_user
                approval.shift_schedule.status = action
                approval.shift_schedule.updated_at = current_time
                shift_schedule_to_update.append(approval.shift_schedule)

            elif approval.approval_type == "edit_time":
                # หาตัว edit attendance ที่ตรงกับ approval นี้
                edit_time = EditTimeAttendance.objects.filter(
                    date=approval.date,
                    status="pending",
                    approve_user=approval.approve_user,
                    user=approval.request_user,
                    branch=approval.branch,
                    timestamp=approval.timestamp,
                ).first()

                if edit_time:
                    edit_time.status = action
                    edit_time.updated_at = current_time
                    edit_time_to_update.append(edit_time)
                    approval.edit_time_attendance = edit_time

    # ✅ ใช้ bulk_update แทนการ save() ทีละตัว
    Approval.objects.bulk_update(approvals_to_update, ["status", "updated_at", "edit_time_attendance"])

    # 🚀 ดึง LeaveBalance ล่วงหน้าทั้งหมดที่เกี่ยวข้อง
    leave_balances = LeaveBalance.objects.filter(
        user__in=[leave.user for leave in leave_attendance_to_update],
        leave_type__in=[leave.leave_type for leave in leave_attendance_to_update]
    )

    # 🗺️ แปลงเป็น dictionary เพื่อเข้าถึงเร็วขึ้น
    balance_map = {
        (lb.user_id, lb.leave_type_id): lb
        for lb in leave_balances
    }

    leave_balances_to_update = []

    for leave in leave_attendance_to_update:
        key = (leave.user_id, leave.leave_type_id)
        leave_balance = balance_map.get(key)

        if not leave_balance:
            continue

        working_hours = calculate_working_hours(leave.user, leave.start_datetime, leave.end_datetime)

        if leave.status == "approved":
            if leave_balance.remaining_hours < working_hours:
                return JsonResponse({
                    "error": f"พนักงาน {leave.user.get_full_name()} มีวันลาคงเหลือไม่เพียงพอ"
                }, status=400)
            leave_balance.remaining_hours -= working_hours

        elif leave.status == "cancelled":
            leave_balance.remaining_hours += working_hours

        leave_balance.updated_at = current_time
        leave_balances_to_update.append(leave_balance)

    # ✅ อัปเดต LeaveBalance แบบ bulk
    if leave_balances_to_update:
        LeaveBalance.objects.bulk_update(leave_balances_to_update, ["remaining_hours", "updated_at"])
    LeaveAttendance.objects.bulk_update(leave_attendance_to_update, ["status", "updated_at"])
    ShiftSchedule.objects.bulk_update(shift_schedule_to_update, ["shift", "shift_day", "approve_user", "status", "updated_at"])
    EditTimeAttendance.objects.bulk_update(edit_time_to_update, ["status", "updated_at"])

    return JsonResponse({"message": f"{len(approvals_to_update)} คำขอได้รับการพิจารณาแล้ว"}, status=200)


@login_required(login_url="log-in")
def bulk_cancel_requests(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)
    approval_ids = data.get("approval_ids", [])

    # ดึงคำขอของผู้ใช้ที่ยัง pending อยู่
    approvals = Approval.objects.select_related(
        "leave_attendance", "edit_time_attendance"
    ).filter(id__in=approval_ids, request_user=request.user, status="pending")

    if not approvals.exists():
        return JsonResponse({"error": "ไม่พบคำขอที่สามารถยกเลิกได้"}, status=400)

    current_time = now()

    approvals_to_update = []
    leave_attendance_to_update = []
    edit_time_to_update = []

    with transaction.atomic():
        for approval in approvals:
            approval.status = "cancelled"
            approval.updated_at = current_time
            approvals_to_update.append(approval)

            # ✅ ย้าย logic จาก signal มาไว้ตรงนี้
            if approval.approval_type == "leave" and approval.leave_attendance:
                lt = approval.leave_attendance
                lt.status = "cancelled"
                lt.updated_at = current_time
                leave_attendance_to_update.append(lt)

            elif approval.approval_type == "edit_time":
                edit_time = EditTimeAttendance.objects.filter(
                    date=approval.date,
                    status="pending",
                    approve_user=approval.approve_user,
                    user=approval.request_user,
                    branch=approval.branch,
                    timestamp=approval.timestamp,
                ).first()

                if edit_time:
                    edit_time.status = "cancelled"
                    edit_time.updated_at = current_time
                    edit_time_to_update.append(edit_time)
                    approval.edit_time_attendance = edit_time  # เชื่อม ref ให้ด้วย

    # ⚡ อัปเดตทั้งหมดแบบ bulk
    Approval.objects.bulk_update(approvals_to_update, ["status", "updated_at", "edit_time_attendance"])
    LeaveAttendance.objects.bulk_update(leave_attendance_to_update, ["status", "updated_at"])
    EditTimeAttendance.objects.bulk_update(edit_time_to_update, ["status", "updated_at"])

    return JsonResponse({"message": f"ยกเลิกคำขอ {len(approvals_to_update)} รายการสำเร็จ"}, status=200)