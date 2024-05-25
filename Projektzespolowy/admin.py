from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from django.http import HttpResponse
from middlewares import login_required
from .coordinates import get_coordinates

@login_required
def get_all_statuses(request):
    if request.method == 'GET':
        try:

            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("""
                SELECT Id, StatusName FROM STATUS
            """)
            statuses = cursor.fetchall()


            conn.close()


            if statuses:
                status_list = [{'Id': status[0], 'StatusName': status[1]} for status in statuses]
                return JsonResponse(status_list, safe=False)
            else:

                return JsonResponse([], safe=False)

        except Exception as e:

            return JsonResponse({'error': str(e)}, status=500)

    else:

        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@login_required
def update_order(request):
    if request.method == 'PUT':
        try:

            order_data = json.loads(request.body)
            order_id = order_data.get('Id')
            status_name = order_data.get('StatusName')
            sender_mail = order_data.get('SenderMail')
            receiver_mail = order_data.get('ReceiverMail')
            payment_method_name = order_data.get('PaymentMethodName')
            description = order_data.get('Description')
            active = order_data.get('Active')
            start_date = order_data.get('StartDate')
            end_date = order_data.get('EndDate')
            machine_id_from = order_data.get('MachineIdFrom')
            machine_id_to = order_data.get('MachineIdTo')
            delivery_date = order_data.get('DeliveryDate')
            return_delivery_date = order_data.get('ReturnDeliveryDate')
            postponed = order_data.get('Postponed')
            postponed_days = order_data.get('PostponedDays')
            is_return = order_data.get('IsReturn')
            delivery_cost = order_data.get('DeliveryCost')
            chamber_id = order_data.get('ChamberId')


            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("SELECT Id FROM STATUS WHERE StatusName = ?", (status_name,))
            status_id = cursor.fetchone()
            if not status_id:
                raise ValueError("Invalid StatusName")
            status_id = status_id[0]

            cursor.execute("SELECT Id FROM USER WHERE Mail = ?", (sender_mail,))
            sender_id = cursor.fetchone()
            if not sender_id:
                raise ValueError("Invalid SenderMail")
            sender_id = sender_id[0]

            cursor.execute("SELECT Id FROM USER WHERE Mail = ?", (receiver_mail,))
            receiver_id = cursor.fetchone()
            if not receiver_id:
                raise ValueError("Invalid ReceiverMail")
            receiver_id = receiver_id[0]

            cursor.execute("SELECT Id FROM PAYMENT_METHOD WHERE PaymentName = ?", (payment_method_name,))
            payment_method_id = cursor.fetchone()
            if not payment_method_id:
                raise ValueError("Invalid PaymentMethodName")
            payment_method_id = payment_method_id[0]


            conn.execute("BEGIN")


            cursor.execute("""
                UPDATE ORDER_
                SET 
                    StatusId = ?, 
                    SenderId = ?, 
                    ReceiverId = ?, 
                    ChamberId = ?, 
                    PaymentMethodId = ?, 
                    Description = ?, 
                    Active = ?, 
                    StartDate = ?, 
                    EndDate = ?, 
                    MachineIdFrom = ?, 
                    MachineIdTo = ?, 
                    DeliveryDate = ?, 
                    ReturnDeliveryDate = ?, 
                    Postponed = ?, 
                    PostponedDays = ?, 
                    IsReturn = ?, 
                    DeliveryCost = ?
                WHERE 
                    Id = ?;
            """, (
                status_id, sender_id, receiver_id, chamber_id, payment_method_id, description, active, start_date, end_date, 
                machine_id_from, machine_id_to, delivery_date, return_delivery_date, postponed, postponed_days, is_return, delivery_cost, order_id
            ))


            conn.commit()


            conn.close()


            return JsonResponse({'success': True, 'message': 'Order updated successfully.'}, status=200)

        except Exception as e:

            conn.rollback()


            conn.close()


            return JsonResponse({'success': False, 'message': f'Error updating order: {str(e)}'}, status=500)


    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def update_machine(request):
    if request.method == 'POST':
        try:

            data = json.loads(request.body)
            machine_id = data.get('Id')
            address = data.get('Address')
            postal_code = data.get('PostalCode')
            location = data.get('Location')


            latitude, longitude = get_coordinates(address, location)

            if latitude is None or longitude is None:
                return JsonResponse({'error': 'Failed to obtain coordinates for the given address'}, status=400)


            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("""
                SELECT Id FROM MACHINE WHERE Id = ?
            """, (machine_id,))
            machine_exists = cursor.fetchone()

            if machine_exists is None:

                conn.close()
                return JsonResponse({'error': 'Machine not found'}, status=404)


            cursor.execute("""
                UPDATE MACHINE
                SET Address = ?, PostalCode = ?, Location = ?, Latitude = ?, Longitude = ?
                WHERE Id = ?
            """, (address, postal_code, location, latitude, longitude, machine_id))


            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Machine updated successfully'}, status=200)

        except Exception as e:

            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    

@login_required
def get_machine_fill_status(request):
    if request.method == 'GET':
        try:

            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            query = """
                SELECT
                    m1.Id,
                    m1.Address,
                    m1.PostalCode,
                    m1.Location,
                    COALESCE(SUM(CASE WHEN c.Status = 0 THEN 1 ELSE 0 END), 0) AS EmptyChambers,
                    COALESCE(SUM(CASE WHEN c.Status = 1 THEN 1 ELSE 0 END), 0) AS OccupiedChambers,
                    CONCAT(
                        CAST(
                            CASE 
                                WHEN COUNT(c.Id) = 0 THEN '0.00'
                                ELSE CAST(ROUND((SUM(CASE WHEN c.Status = 1 THEN 1 ELSE 0 END) * 100.0) / COUNT(c.Id), 2) AS VARCHAR(6))
                            END AS VARCHAR(6)
                        ), '%') AS OccupiedPercentage,
                    COALESCE(COUNT(DISTINCT m2.Id), 0) AS MobileMachines,
                    COALESCE(COUNT(DISTINCT m3.Id), 0) AS VerticalMachines
                FROM
                    MACHINE m1
                LEFT JOIN (
                    SELECT
                        c.*,
                        m.Address,
                        m.PostalCode,
                        m.Location
                    FROM
                        CHAMBER c
                    JOIN MACHINE m ON c.MachineId = m.Id
                ) c ON m1.Address = c.Address AND m1.PostalCode = c.PostalCode AND m1.Location = c.Location
                LEFT JOIN MACHINE m2 ON m1.Address = m2.Address AND m1.PostalCode = m2.PostalCode AND m1.Location = m2.Location AND m2.IdMachineType = 2
                LEFT JOIN MACHINE m3 ON m1.Address = m3.Address AND m1.PostalCode = m3.PostalCode AND m1.Location = m3.Location AND m3.IdMachineType = 3
                WHERE
                    m1.IdMachineType = 1
                GROUP BY
                    m1.Id, m1.Address, m1.PostalCode, m1.Location
                ORDER BY
                    COALESCE(SUM(CASE WHEN c.Status = 1 THEN 1 ELSE 0 END), 0) * 1.0 /
                    (COALESCE(SUM(CASE WHEN c.Status = 0 THEN 1 ELSE 0 END), 0) + COALESCE(SUM(CASE WHEN c.Status = 1 THEN 1 ELSE 0 END), 0)) DESC;
            """

            cursor.execute(query)
            machines = cursor.fetchall()


            machines_list = [
                {
                    'Id': machine[0],
                    'Address': machine[1],
                    'PostalCode': machine[2],
                    'Location': machine[3],
                    'EmptyChambers': machine[4],
                    'OccupiedChambers': machine[5],
                    'OccupiedPercentage': machine[6],
                    'MobileMachines': machine[7],
                    'VerticalMachines': machine[8]
                }
                for machine in machines
            ]


            conn.close()


            return JsonResponse({'machines': machines_list}, status=200)

        except Exception as e:

            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@login_required
def assign_machine(request):
    if request.method == 'POST':
        try:

            data = json.loads(request.body)
            machine_id = data.get('machine_id')
            id_machine_type = data.get('id_machine_type')


            if not machine_id or not id_machine_type:
                return JsonResponse({'error': 'Invalid input data'}, status=400)


            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("SELECT Address, PostalCode, Location FROM MACHINE WHERE Id = ?", (machine_id,))
            machine_details = cursor.fetchone()

            if not machine_details:
                conn.close()
                return JsonResponse({'error': 'Machine not found'}, status=404)

            address, postal_code, location = machine_details


            if id_machine_type == 2:
                cursor.execute("""
                    SELECT COUNT(*) FROM MACHINE 
                    WHERE Address = ? AND PostalCode = ? AND Location = ? AND IdMachineType = 2
                """, (address, postal_code, location))
                mobile_count = cursor.fetchone()[0]

                if mobile_count >= 1:
                    conn.close()
                    return JsonResponse({'error': 'Only one mobile machine can be assigned'}, status=400)

            elif id_machine_type == 3:
                cursor.execute("""
                    SELECT COUNT(*) FROM MACHINE 
                    WHERE Address = ? AND PostalCode = ? AND Location = ? AND IdMachineType = 3
                """, (address, postal_code, location))
                vertical_count = cursor.fetchone()[0]

                if vertical_count >= 3:
                    conn.close()
                    return JsonResponse({'error': 'Only up to three vertical machines can be assigned'}, status=400)


            cursor.execute("""
                SELECT Id FROM MACHINE 
                WHERE Address = '-' AND PostalCode = '-' AND Location = '-' AND IdMachineType = ?
                LIMIT 1
            """, (id_machine_type,))
            available_machine = cursor.fetchone()

            if not available_machine:
                conn.close()
                return JsonResponse({'error': 'No available machines to assign'}, status=404)

            available_machine_id = available_machine[0]


            cursor.execute("""
                UPDATE MACHINE SET Address = ?, PostalCode = ?, Location = ? 
                WHERE Id = ?
            """, (address, postal_code, location, available_machine_id))


            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Machine assigned successfully'}, status=200)

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@login_required
def unassign_machine(request):
    if request.method == 'POST':
        try:

            data = json.loads(request.body)
            machine_id = data.get('machine_id')
            id_machine_type = data.get('id_machine_type')


            if not machine_id or not id_machine_type or id_machine_type == 1:
                return JsonResponse({'error': 'Invalid input data'}, status=400)


            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("SELECT Address, PostalCode, Location FROM MACHINE WHERE Id = ? AND IdMachineType = 1", (machine_id,))
            machine_details = cursor.fetchone()

            if not machine_details:
                conn.close()
                return JsonResponse({'error': 'Machine not found'}, status=404)

            address, postal_code, location = machine_details


            cursor.execute("""
                SELECT Id FROM MACHINE 
                WHERE Address = ? AND PostalCode = ? AND Location = ? AND IdMachineType = ?
            """, (address, postal_code, location, id_machine_type))
            assigned_machine = cursor.fetchone()

            if not assigned_machine:
                conn.close()
                return JsonResponse({'error': 'No assigned machine found'}, status=404)

            assigned_machine_id = assigned_machine[0]


            cursor.execute("""
                SELECT COUNT(*) FROM ORDER_ 
                WHERE ChamberId IN (SELECT Id FROM CHAMBER WHERE MachineId = ?) AND Active = 1
            """, (assigned_machine_id,))
            active_order_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM ORDER_CHAMBER 
                WHERE ChamberId IN (SELECT Id FROM CHAMBER WHERE MachineId = ?)
            """, (assigned_machine_id,))
            order_chamber_count = cursor.fetchone()[0]

            if active_order_count > 0 or order_chamber_count > 0:
                conn.close()
                return JsonResponse({'error': 'Cannot unassign machine with active orders or order chambers'}, status=400)


            cursor.execute("""
                UPDATE MACHINE SET Address = '-', PostalCode = '-', Location = '-' 
                WHERE Id = ?
            """, (assigned_machine_id,))


            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Machine unassigned successfully'}, status=200)

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)   