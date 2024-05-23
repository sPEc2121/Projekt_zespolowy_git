from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required

@login_required
def get_all_machines(request, user_id):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            MACHINE.Id, 
            MACHINE.Address, 
            MACHINE.PostalCode, 
            MACHINE.Location, 
            MACHINE.Country, 
            MACHINE.IdMachineType, 
            MACHINE.Latitude, 
            MACHINE.Longitude,
            CASE 
                WHEN FAVOURITE_MACHINES.MachineId IS NOT NULL THEN 1 
                ELSE 0 
            END AS IsFav
        FROM 
            MACHINE
        LEFT JOIN 
            FAVOURITE_MACHINES ON MACHINE.Id = FAVOURITE_MACHINES.MachineId AND FAVOURITE_MACHINES.UserId = ?
    """, (user_id,))

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
            'IdMachineType': machine[5],
            'Latitude': machine[6],
            'Longitude': machine[7],
            'IsFav': bool(machine[8])
        }
        machines_list.append(machine_dict)

    return JsonResponse(machines_list, safe=False)

@login_required
def get_available_machines_by_size(request, size, user_id):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    WITH AvailableMachines AS (
    SELECT 
        MACHINE.Id AS MachineId,
        MACHINE.Address,
        MACHINE.PostalCode,
        MACHINE.Location,
        MACHINE.Latitude,
        MACHINE.Longitude,
        CASE 
            WHEN FAVOURITE_MACHINES.MachineId IS NOT NULL THEN 1 
            ELSE 0 
        END AS IsFav,
        MACHINE.IdMachineType,
        EXISTS (
            SELECT 1
            FROM CHAMBER C
            WHERE 
                C.MachineId = MACHINE.Id
                AND C.Status = 0
                AND C.Size = ?
                AND NOT EXISTS (
                    SELECT 1
                    FROM ORDER_CHAMBER OC
                    JOIN ORDER_ O ON OC.OrderId = O.Id
                    WHERE 
                        OC.ChamberId = C.Id
                        AND O.StartDate BETWEEN ? AND ?
                )
        ) AS HasFreeChamber
    FROM 
        MACHINE
    LEFT JOIN 
        FAVOURITE_MACHINES ON MACHINE.Id = FAVOURITE_MACHINES.MachineId AND FAVOURITE_MACHINES.UserId = ?
)

SELECT DISTINCT
    M1.MachineId,
    M1.Address,
    M1.PostalCode,
    M1.Location,
    M1.Latitude,
    M1.Longitude,
    M1.IsFav
FROM 
    AvailableMachines M1
WHERE 
    M1.IdMachineType = 1 
    AND (
        M1.HasFreeChamber = 1
        OR EXISTS (
            SELECT 1
            FROM AvailableMachines M2
            WHERE 
                M2.Address = M1.Address
                AND M2.PostalCode = M1.PostalCode
                AND M2.Location = M1.Location
                AND M2.IdMachineType <> 1
                AND M2.HasFreeChamber = 1
        )
    )
    """, (size, three_days_ago, current_date, user_id))

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
            'Longitude': machine[5],
            'IsFav': bool(machine[6])
        })

    return JsonResponse(machines_list, safe=False)

@login_required
def add_favourite_machine(request, user_id, machine_id):
    if request.method == 'POST':
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT COUNT(*) FROM FAVOURITE_MACHINES WHERE UserId = ? AND MachineId = ?
            """, (user_id, machine_id))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return JsonResponse({'error': 'Machine already added to favourites'}, status=400)

            cursor.execute("""
            INSERT INTO FAVOURITE_MACHINES (UserId, MachineId)
            VALUES (?, ?)
            """, (user_id, machine_id))

            conn.commit()

            conn.close()

            return JsonResponse({'success': True, 'message': 'Machine added to favourites'}, status=201)
        except Exception as e:
            conn.rollback()

            conn.close()

            return JsonResponse({'success': False, 'message': f'Error adding machine to favourites: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Unsupported method'}, status=405)

@login_required
def remove_favourite_machine(request, user_id, machine_id):
    if request.method == 'POST':
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        try:

            cursor.execute("""
            SELECT COUNT(*) FROM FAVOURITE_MACHINES WHERE UserId = ? AND MachineId = ?
            """, (user_id, machine_id))
            if cursor.fetchone()[0] == 0:
                conn.close()
                return JsonResponse({'error': 'Machine not found in favourites'}, status=404)

            cursor.execute("""
            DELETE FROM FAVOURITE_MACHINES WHERE UserId = ? AND MachineId = ?
            """, (user_id, machine_id))

            conn.commit()

            conn.close()

            return JsonResponse({'success': True, 'message': 'Machine removed from favourites'}, status=200)
        except Exception as e:

            conn.rollback()

            conn.close()

            return JsonResponse({'success': False, 'message': f'Error removing machine from favourites: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Unsupported method'}, status=405)



