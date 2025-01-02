from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from user_app.models import User, Approval
from .models import LeaveAttendance
from .forms import LeaveAttendanceForm


def leave_request_view(request):
    if request.method == 'POST':
        form = LeaveAttendanceForm(request.POST)
        uid = request.POST.get('uid')  # รับ `uid` จาก LINE Login
        user = get_object_or_404(User, uid=uid)  # ค้นหา User โดย `uid`

        # หาผู้อนุมัติจาก Approval
        position = user.position
        if not position:
            messages.error(request, "User does not have a position assigned.")
            return redirect('leave-request')

        approvers = Approval.objects.filter(approved=position, is_active=True).values_list('approver__id', flat=True)

        if not approvers:
            messages.error(request, "No approvers assigned for this user's position.")
            return redirect('leave-request')

        if form.is_valid():
            leave = form.save(commit=False)
            leave.user = user
            leave.approve_user_id = approvers[0]  # กำหนดผู้อนุมัติคนแรกในลิสต์
            leave.status = 'pending'
            leave.save()
            messages.success(request, "Leave request submitted successfully!")
            return redirect('leave-request')
    else:
        form = LeaveAttendanceForm()

    return render(request, 'attendance_app/leave_request.html', {'form': form})
