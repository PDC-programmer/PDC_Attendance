"""
URL configuration for pdc_attendance_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


# def login_view(request):
#     return render(request, 'account/login.html', {'LINE_LOG_IN_CHANNEL_ID': settings.LINE_LOG_IN_CHANNEL_ID})


urlpatterns = [
    # path('accounts/login/', login_view),
    path('', include('general_app.urls')),
    path('user/', include('user_app.urls')),
    path('attendance/', include('attendance_app.urls')),
    path('line/', include('line_app.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Add this for allauth
    path('approval/', include('approval_app.urls')),  # Add this for allauth
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)