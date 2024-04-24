"""
URL configuration for Projektzespolowy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.urls import path
from . import views, user, authorize

urlpatterns = [
    path('get-all-users/', user.get_all_users, name='get_all_users'),
    path('disable-user/', user.disable_user, name='disable-user'),
    path('login/', authorize.login, name='login'),
    path('register/', authorize.register, name='register'),
    path('admin/', admin.site.urls),
]
