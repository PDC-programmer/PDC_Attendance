from django.contrib import admin
from .models import User, Position, Department, Approval

admin.site.register(User)
admin.site.register(Position)
admin.site.register(Department)
admin.site.register(Approval)
