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
from . import views, user, authorize, orders, payment, machines

urlpatterns = [
    path('get-all-users/', user.get_all_users, name='get_all_users'),
    path('disable-user/', user.disable_user, name='disable-user'),
    path('get-user-by-id/<int:user_id>/', user.get_user_by_id, name='get_user_by_id'),
    path('edit-user/<int:user_id>/', user.edit_user, name='edit_user'),
    path('get-all-orders/', orders.get_all_orders, name='get_all_orders'),
    path('create-order/', orders.create_order, name='create_order'),
    path('get-all-payment-methods/', payment.get_all_payment_methods, name='get_all_payment_methods'),
    path('get-all-machines/', machines.get_all_machines, name='get_all_machines'),
    path('get-all-available-machines/', machines.get_all_available_machines, name='get_all_available_machines'),
    path('login/', authorize.login, name='login'),
    path('register/', authorize.register, name='register'),
    # path('admin/', admin.site.urls),
]
