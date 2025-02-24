from django.contrib import admin
from .models import *
admin.site.register(LeaveType)
admin.site.register(LeaveAttendance)
admin.site.register(LeaveBalance)
admin.site.register(Shift)
admin.site.register(ShiftSchedule)
admin.site.register(PublicHoliday)

