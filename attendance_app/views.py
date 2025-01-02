from django.shortcuts import render
from django.http import JsonResponse
from user_app.models import User, Approval, Position
from attendance_app.models import LeaveAttendance


def leave_request_view(request):
    if request.method == "POST":
        user_uid = request.POST.get("uid")
        leave_type = request.POST.get("type")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")

        # Check if the user exists
        user = User.objects.filter(uid=user_uid).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Get the approver from the Approval table
        position = user.position
        approver_positions = Approval.objects.filter(approved=position, is_active=True).values_list('approver',
                                                                                                    flat=True)
        approver = User.objects.filter(position_id__in=approver_positions).first()

        if not approver:
            return JsonResponse({"error": "Approver not found"}, status=404)

        # Save LeaveAttendance
        LeaveAttendance.objects.create(
            user=user,
            approve_user=approver,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            type=leave_type,
        )

        return JsonResponse({"message": "Leave request submitted successfully"})

    return render(request, "attendance_app/leave_request.html")
