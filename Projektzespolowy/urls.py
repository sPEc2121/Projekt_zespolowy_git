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
from . import views, user, authorize, orders, payment, machines, admin

urlpatterns = [
    path('get-all-users/', user.get_all_users, name='get_all_users'),
    path('disable-user/', user.disable_user, name='disable-user'),
    path('enable-user/', user.enable_user, name='enable_user'),
    path('get-user-by-id/<int:user_id>/', user.get_user_by_id, name='get_user_by_id'),
    path('edit-user/<int:user_id>/', user.edit_user, name='edit_user'),
    path('get-all-orders/', orders.get_all_orders, name='get_all_orders'),
    path('create-order/', orders.create_order, name='create_order'),
    path('get-user-orders/<int:user_id>/', orders.get_user_orders, name='get_user_orders'),
    path('change-order-status/<int:order_id>/<int:status_id>/', orders.change_order_status, name='change_order_status'),
    path('update-order-status-by-chamber/<int:chamber_id>/', orders.update_order_status_by_chamber, name='update_order_status_by_chamber'),
    path('postpone-order/', orders.postpone_order, name='postpone_order'),
    path('get-all-payment-methods/', payment.get_all_payment_methods, name='get_all_payment_methods'),
    path('get-size-prices/', payment.get_size_prices, name='get_size_prices'),
    path('get-all-machines/<int:user_id>/', machines.get_all_machines, name='get_all_machines'),
    path('get-available-machines-by-size/<str:size>/<int:user_id>/', machines.get_available_machines_by_size, name='get_available_machines_by_size'),
    path('add-favourite-machine/<int:user_id>/<int:machine_id>/', machines.add_favourite_machine, name='add_favourite_machine'),
    path('remove-favourite-machine/<int:user_id>/<int:machine_id>/', machines.remove_favourite_machine, name='remove_favourite_machine'),
    path('login/', authorize.login, name='login'),
    path('register/', authorize.register, name='register'),
    path('get-all-statuses/', admin.get_all_statuses, name='get_all_statuses'),
    path('update-order/', admin.update_order, name='update_order'),
    path('update-machine/', admin.update_machine, name='update_machine'),
    path('get-machine-fill-status/', admin.get_machine_fill_status, name='get_machine_fill_status'),
    path('assign-machine/', admin.assign_machine, name='assign_machine'),
    path('generate-plot/', admin.generate_plot, name='generate_plot'),
    # path('admin/', admin.site.urls),
]
