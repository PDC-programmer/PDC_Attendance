from django.shortcuts import render
from django.http import JsonResponse
from user_app.models import User, BsnStaff
from attendance_app.models import LeaveAttendance
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def leave_request_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data.get("userID")
        start_date = data.get("startDate")
        end_date = data.get("endDate")
        reason = data.get("reason")
        leave_type = data.get("type")

        # ค้นหา User ที่มี UID ตรงกับ userID
        user = User.objects.filter(uid=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # ค้นหาผู้อนุมัติจากตาราง BsnStaff
        staff = BsnStaff.objects.filter(django_usr_id=user).first()
        if not staff or not staff.mng_staff_id:
            return JsonResponse({"error": "Approver not found"}, status=404)

        approver_user = User.objects.filter(id=staff.mng_staff_id).first()
        if not approver_user:
            return JsonResponse({"error": "Approver user not found"}, status=404)

        # สร้าง LeaveAttendance
        LeaveAttendance.objects.create(
            user=user,
            approve_user=approver_user,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            type=leave_type,
        )

        return JsonResponse({"message": "Leave request submitted successfully"}, status=201)

    return render(request, "attendance/leave_request.html")
