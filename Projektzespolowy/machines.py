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
        SELECT Id, Address, PostalCode, Location, Country, IsMobile, Latitude, Longitude FROM MACHINE
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
            'IsMobile': bool(machine[5]),
            'Latitude': machine[6],
            'Longitude':machine[7]
        }
        machines_list.append(machine_dict)

    return JsonResponse(machines_list, safe=False)

@login_required
def get_available_machines_by_size(request, size):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    SELECT DISTINCT
            MACHINE.Id AS MachineId,
            MACHINE.Address,
            MACHINE.PostalCode,
            MACHINE.Location,
            MACHINE.Latitude,
            MACHINE.Longitude              
        FROM 
            MACHINE 
        LEFT JOIN 
            CHAMBER 
        ON 
            MACHINE.Id = CHAMBER.MachineId
        WHERE 
            CHAMBER.Status = 0 AND
            CHAMBER.Size = ? AND
            NOT EXISTS (
                SELECT 1 
                FROM 
                    ORDER_CHAMBER 
                JOIN 
                    ORDER_ 
                ON 
                    ORDER_CHAMBER.OrderId = ORDER_.Id 
                WHERE 
                    ORDER_CHAMBER.ChamberId = CHAMBER.Id AND 
                    ORDER_.StartDate BETWEEN ? AND ?
            )
    """, (size, three_days_ago, current_date))

    machines = cursor.fetchall()

    conn.close()

    if not machines:
        return JsonResponse({'error': f'No machines available for size {size}'}, status=404)

    machines_list = []
    for machine in machines:
        machines_list.append({
            'Id': machine[0],
            'Address': machine[1],
            'PostalCode': machine[2],
            'Location': machine[3],
            'Latitude': machine[4],
            'Longitude': machine[5]
        })

    return JsonResponse(machines_list, safe=False)
