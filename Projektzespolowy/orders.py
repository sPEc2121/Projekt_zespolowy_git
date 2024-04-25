from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required

@login_required
def get_all_orders(request):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            ORDER_.Id, 
            STATUS.StatusName, 
            Sender.Mail AS SenderMail, 
            Receiver.Mail AS ReceiverMail, 
            CHAMBER.Size, 
            PAYMENT_METHOD.PaymentName, 
            ORDER_.Description, 
            ORDER_.Active, 
            ORDER_.StartDate, 
            ORDER_.EndDate, 
            ORDER_.MachineIdFrom, 
            ORDER_.MachineIdTo, 
            ORDER_.DeliveryDate, 
            ORDER_.ReturnDeliveryDate, 
            ORDER_.Postponed, 
            ORDER_.PostponedDays, 
            ORDER_.IsReturn, 
            ORDER_.DeliveryCost 
        FROM 
            ORDER_ 
        LEFT JOIN 
            STATUS 
        ON 
            ORDER_.StatusId = STATUS.Id 
        LEFT JOIN 
            USER AS Sender 
        ON 
            ORDER_.SenderId = Sender.Id 
        LEFT JOIN 
            USER AS Receiver 
        ON 
            ORDER_.ReceiverId = Receiver.Id 
        LEFT JOIN 
            CHAMBER 
        ON 
            ORDER_.ChamberId = CHAMBER.Id 
        LEFT JOIN 
            PAYMENT_METHOD 
        ON 
            ORDER_.PaymentMethodId = PAYMENT_METHOD.Id
    """)

    orders = cursor.fetchall()

    conn.close()

    orders_list = []
    for order in orders:
        order_dict = {
            'Id': order[0],
            'StatusName': order[1],
            'SenderMail': order[2],
            'ReceiverMail': order[3],
            'ChamberSize': order[4],
            'PaymentMethodName': order[5],
            'Description': order[6],
            'Active': bool(order[7]),
            'StartDate': order[8],
            'EndDate': order[9],
            'MachineIdFrom': order[10],
            'MachineIdTo': order[11],
            'DeliveryDate': order[12],
            'ReturnDeliveryDate': order[13],
            'Postponed': bool(order[14]),
            'PostponedDays': order[15],
            'IsReturn': bool(order[16]),
            'DeliveryCost': order[17]
        }
        orders_list.append(order_dict)

    return JsonResponse(orders_list, safe=False)
