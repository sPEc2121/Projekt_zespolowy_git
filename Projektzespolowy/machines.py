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

@login_required
def get_all_available_machines(request):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
            MACHINE.Id AS MachineId,
            MACHINE.Address,
            MACHINE.PostalCode,
            MACHINE.Location,
            MACHINE.Country,
            MACHINE.IsMobile,
            CHAMBER.Size AS ChamberSize
        FROM 
            MACHINE 
        LEFT JOIN 
            CHAMBER 
        ON 
            MACHINE.Id = CHAMBER.MachineId AND CHAMBER.Status = 0
        WHERE 
            EXISTS (
                SELECT 
                    1 
                FROM 
                    CHAMBER AS C 
                WHERE 
                    C.MachineId = MACHINE.Id AND 
                    C.Status = 0
            )
    """)

    machines = cursor.fetchall()

    conn.close()

    machines_list = {}
    for machine in machines:
        machine_id = machine[0]
        if machine_id not in machines_list:
            machines_list[machine_id] = {
                'Id': machine_id,
                'Address': machine[1],
                'PostalCode': machine[2],
                'Location': machine[3],
                'Country': machine[4],
                'IsMobile': bool(machine[5]),
                'AvailableSizes': set()
            }
        machines_list[machine_id]['AvailableSizes'].add(machine[6])

    for machine_id in machines_list:
        machines_list[machine_id]['AvailableSizes'] = list(machines_list[machine_id]['AvailableSizes'])

    return JsonResponse(list(machines_list.values()), safe=False)