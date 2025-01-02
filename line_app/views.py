from django.shortcuts import render
from user_app.models import User


# Create your views here.
def register(request):
    return render(request, 'line_app/register.html')
