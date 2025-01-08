from django.contrib import admin
from .models import LeaveType, LeaveAttendance, LeaveBalance

admin.site.register(LeaveType)
admin.site.register(LeaveAttendance)
admin.site.register(LeaveBalance)

