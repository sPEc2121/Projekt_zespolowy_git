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

@login_required
def get_size_prices(request):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
    WITH CTE_S AS (
    SELECT Id
    FROM CHAMBER
    WHERE Size = 'S'
    ORDER BY Id
    LIMIT 1
),
CTE_M AS (
    SELECT Id
    FROM CHAMBER
    WHERE Size = 'M'
    ORDER BY Id
    LIMIT 1
),
CTE_L AS (
    SELECT Id
    FROM CHAMBER
    WHERE Size = 'L'
    ORDER BY Id
    LIMIT 1
),
SelectedChambers AS (
    SELECT Id FROM CTE_S
    UNION ALL
    SELECT Id FROM CTE_M
    UNION ALL
    SELECT Id FROM CTE_L
)
SELECT c.Size, cs.Price + 600 AS Price
FROM CHAMBER_DETAILS cs
INNER JOIN CHAMBER c ON cs.ChamberId = c.Id
WHERE cs.ChamberId IN (SELECT Id FROM SelectedChambers)
AND cs.Active = 1;
    """)

    size_prices = cursor.fetchall()

    conn.close()

    size_prices_list = []
    for size_price in size_prices:
        size_price_dict = {
            'Size': size_price[0],
            'Price': size_price[1]
        }
        size_prices_list.append(size_price_dict)

    return JsonResponse(size_prices_list, safe=False)