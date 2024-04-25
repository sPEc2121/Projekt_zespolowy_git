from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required

@login_required
def get_all_payment_methods(request):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Id, PaymentName FROM PAYMENT_METHOD
    """)

    payment_methods = cursor.fetchall()

    conn.close()

    payment_methods_list = []
    for method in payment_methods:
        method_dict = {
            'Id': method[0],
            'PaymentName': method[1]
        }
        payment_methods_list.append(method_dict)

    return JsonResponse(payment_methods_list, safe=False)