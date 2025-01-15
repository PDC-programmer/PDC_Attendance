from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount


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
