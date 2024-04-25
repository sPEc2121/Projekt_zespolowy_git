from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required

@login_required
def get_all_machines(request):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Id, Address, PostalCode, Location, Country, IsMobile FROM MACHINE
    """)

    machines = cursor.fetchall()

    conn.close()

    machines_list = []
    for machine in machines:
        machine_dict = {
            'Id': machine[0],
            'Address': machine[1],
            'PostalCode': machine[2],
            'Location': machine[3],
            'Country': machine[4],
            'IsMobile': bool(machine[5])
        }
        machines_list.append(machine_dict)

    return JsonResponse(machines_list, safe=False)