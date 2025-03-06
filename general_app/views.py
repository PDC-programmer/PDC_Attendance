from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from attendance_app.models import LeaveAttendance
from user_app.models import User
from approval_app.models import Approval


# Create your views here.
def log_in(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'general/login.html')


def log_out(request):
    logout(request)
    return redirect('/')


@login_required(login_url='log-in')
def home(request):
    return render(request, 'general/home.html')


@login_required
def get_pending_leave_attendances(request):
    requester_approval = Approval.objects.filter(request_user=request.user, status="pending")
    # if not User.objects.filter(username=request.user, groups=3).exists():
    #     approver_pending = 0
    approver_approval = Approval.objects.filter(approve_user=request.user, status="pending")

    requester_pending = requester_approval.count()
    approver_pending = approver_approval.count()
    return JsonResponse({
        "requester_pending": requester_pending,
        "approver_pending": approver_pending,
    }, status=200)
