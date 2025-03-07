from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from .models import Approval
from attendance_app.models import LeaveAttendance, ShiftSchedule
from django.shortcuts import render
import json
from attendance_app.utils import calculate_working_hours  # Import the utility function


@login_required(login_url='log-in')
def approve_request(request, approval_id, action):
    """
    อนุมัติหรือปฏิเสธคำขอการลา (LeaveAttendance) หรือ เปลี่ยนกะ (ShiftSchedule)
    """
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

    return render(request, "approval_app/approval_list.html", {
        "approvals": approvals,
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

    return render(request, "approval_app/approval_list_reqeust_user.html", {
        "approvals": approvals,
        "search_query": search_query,
        "approval_type_filter": approval_type_filter,
        "status": status,
    })


@login_required(login_url="log-in")
def bulk_approve_requests(request):
    if request.method == "POST":
        data = json.loads(request.body)
        approval_ids = data.get("approval_ids", [])
        action = data.get("action")

        if action not in ["approved", "rejected"]:
            return JsonResponse({"error": "Invalid action"}, status=400)

        approvals = Approval.objects.filter(id__in=approval_ids, status="pending")

        updated_count = 0
        for approval in approvals:
            approval.status = action  # เปลี่ยนสถานะเป็น approved หรือ rejected
            approval.updated_at = now()
            approval.save()  # ใช้ .save() แทน .update()
            updated_count += 1

        return JsonResponse({"message": f"{updated_count} คำขอได้รับการอัปเดตแล้ว"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required(login_url="log-in")
def bulk_cancel_requests(request):
    """ API สำหรับยกเลิกคำขอที่เลือก """
    if request.method == "POST":
        data = json.loads(request.body)
        approval_ids = data.get("approval_ids", [])

        approvals = Approval.objects.filter(id__in=approval_ids, request_user=request.user, status="pending")
        if not approvals.exists():
            return JsonResponse({"error": "ไม่พบคำขอที่สามารถยกเลิกได้"}, status=400)

        # ใช้ save() แทน update()
        for approval in approvals:
            approval.status = "cancelled"
            approval.save()  # ใช้ save() เพื่อเรียก triggers หรือ signals

        return JsonResponse({"message": f"ยกเลิกคำขอ {approvals.count()} รายการสำเร็จ"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)