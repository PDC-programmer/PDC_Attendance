from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from attendance_app.models import LeaveAttendance
from user_app.models import User


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
    requester_leave_attendances = LeaveAttendance.objects.filter(user=request.user, status="pending")
    # if not User.objects.filter(username=request.user, groups=3).exists():
    #     approver_pending = 0
    approver_leave_attendances = LeaveAttendance.objects.filter(approve_user=request.user, status="pending")

    requester_pending = requester_leave_attendances.count()
    approver_pending = approver_leave_attendances.count()
    return JsonResponse({
        "requester_pending": requester_pending,
        "approver_pending": approver_pending,
    }, status=200)
