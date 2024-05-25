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
            CHAMBER.Id AS ChamberId, 
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
            'ChamberId': order[12],
            'DeliveryDate': order[13],
            'ReturnDeliveryDate': order[14],
            'Postponed': bool(order[15]),
            'PostponedDays': order[16],
            'IsReturn': bool(order[17]),
            'DeliveryCost': order[18]
        }
        orders_list.append(order_dict)

    return JsonResponse(orders_list, safe=False)

@login_required
def create_order(request):
    try:

        order_data = json.loads(request.body)

        sender_mail = order_data.get('SenderMail')
        receiver_mail = order_data.get('ReceiverMail')
        payment_method_id = order_data.get('PaymentMethodId')
        description = order_data.get('Description')
        machine_id_from = order_data.get('MachineIdFrom')
        machine_id_to = order_data.get('MachineIdTo')
        size = order_data.get('Size')


        status_id = 1
        active = 1
        start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_return = 0


        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()


        conn.execute("BEGIN")


        cursor.execute("SELECT Id FROM USER WHERE Mail = ?", (sender_mail,))
        sender_id = cursor.fetchone()
        if sender_id is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'Sender not found'}, status=404)
        sender_id = sender_id[0]


        cursor.execute("SELECT Id FROM USER WHERE Mail = ?", (receiver_mail,))
        receiver_id = cursor.fetchone()
        if receiver_id is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'Receiver not found'}, status=404)
        receiver_id = receiver_id[0]

        def find_available_chamber(machine_id, size):

            cursor.execute("""
                SELECT CHAMBER.Id
                FROM CHAMBER
                WHERE CHAMBER.MachineId = ? AND CHAMBER.Size = ? AND CHAMBER.Status = 0
                LIMIT 1
            """, (machine_id, size))
            chamber = cursor.fetchone()

            if chamber is None:

                cursor.execute("""
                    SELECT C.Id, M1.Id AS OriginalMachineId
                    FROM MACHINE M1
                    JOIN MACHINE M2 ON M1.Address = M2.Address 
                        AND M1.PostalCode = M2.PostalCode 
                        AND M1.Location = M2.Location
                    JOIN CHAMBER C ON M2.Id = C.MachineId
                    WHERE M1.Id = ? AND C.Size = ? AND C.Status = 0
                    LIMIT 1
                """, (machine_id, size))
                alternate_chamber = cursor.fetchone()

                if alternate_chamber is not None:
                    return alternate_chamber[0], machine_id
                else:
                    return None, None
            else:
                return chamber[0], machine_id


        chamber_id_from, valid_machine_id_from = find_available_chamber(machine_id_from, size)
        if chamber_id_from is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'No available chamber found for the selected from machine and size'}, status=400)


        chamber_id_to, valid_machine_id_to = find_available_chamber(machine_id_to, size)
        if chamber_id_to is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'No available chamber found for the selected to machine and size'}, status=400)


        cursor.execute("SELECT Price FROM CHAMBER_DETAILS WHERE ChamberId = ? AND Active = 1", (chamber_id_to,))
        chamber_details = cursor.fetchone()

        if chamber_details:
            delivery_cost = chamber_details[0] + 500
        else:
            delivery_cost = 0


        cursor.execute("""
            INSERT INTO ORDER_ (
                StatusId, 
                SenderId, 
                ReceiverId, 
                ChamberId, 
                PaymentMethodId, 
                Description, 
                Active, 
                StartDate, 
                MachineIdFrom, 
                MachineIdTo,
                IsReturn,
                DeliveryCost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            status_id,
            sender_id,
            receiver_id,
            chamber_id_from,
            payment_method_id,
            description,
            active,
            start_date,
            valid_machine_id_from,
            valid_machine_id_to,
            is_return,
            delivery_cost
        ))


        order_id = cursor.lastrowid


        cursor.execute("""
            INSERT INTO ORDER_CHAMBER (
                OrderId, 
                ChamberId
            ) VALUES (?, ?)
        """, (
            order_id,
            chamber_id_to
        ))


        cursor.execute("""
            UPDATE CHAMBER
            SET Status = 1
            WHERE Id = ?
        """, (chamber_id_from,))


        cursor.execute("""
            UPDATE CHAMBER
            SET Status = 1
            WHERE Id = ?
        """, (chamber_id_to,))


        conn.commit()
        conn.close()

        return JsonResponse({'message': 'Order created successfully'})

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_user_orders(request, user_id):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            ORDER_.Id, 
            STATUS.StatusName, 
            Sender.Mail AS SenderMail, 
            Receiver.Mail AS ReceiverMail, 
            CHAMBER.Id AS ChamberId, 
            PAYMENT_METHOD.PaymentName, 
            ORDER_.Description, 
            ORDER_.Active, 
            ORDER_.StartDate, 
            ORDER_.EndDate, 
            UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(SUBSTR(MACHINE_FROM.Location, 1, 3), 'ą', 'A'), 'ć', 'C'), 'ę', 'E'), 'ł', 'L'), 'ń', 'N'), 'ó', 'O'), 'ś', 'S'), 'ź', 'Z'), 'ż', 'Z'), 'Ą', 'A'), 'Ć', 'C'), 'Ę', 'E'), 'Ł', 'L'), 'Ń', 'N'), 'Ó', 'O'), 'Ś', 'S'), 'Ź', 'Z'), 'Ż', 'Z')) || MACHINE_FROM.Id AS MachineCodeFrom,
            UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(SUBSTR(MACHINE_TO.Location, 1, 3), 'ą', 'A'), 'ć', 'C'), 'ę', 'E'), 'ł', 'L'), 'ń', 'N'), 'ó', 'O'), 'ś', 'S'), 'ź', 'Z'),'ż', 'Z'), 'Ą', 'A'), 'Ć', 'C'), 'Ę', 'E'), 'Ł', 'L'), 'Ń', 'N'), 'Ó', 'O'), 'Ś', 'S'), 'Ź', 'Z'), 'Ż', 'Z')) || MACHINE_TO.Id AS MachineCodeTo,
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
        LEFT JOIN 
            MACHINE AS MACHINE_FROM
        ON 
            ORDER_.MachineIdFrom = MACHINE_FROM.Id
        LEFT JOIN 
            MACHINE AS MACHINE_TO
        ON 
            ORDER_.MachineIdTo = MACHINE_TO.Id
        WHERE 
            ORDER_.SenderId = ? OR ORDER_.ReceiverId = ?
    """, (user_id, user_id))

    orders = cursor.fetchall()

    conn.close()

    if not orders:
        return JsonResponse({'error': 'User with the specified ID not found'}, status=404)

    orders_list = []
    for order in orders:
        order_dict = {
            'Id': order[0],
            'StatusName': order[1],
            'SenderMail': order[2],
            'ReceiverMail': order[3],
            'ChamberId': order[4],
            'PaymentMethodName': order[5],
            'Description': order[6],
            'Active': bool(order[7]),
            'StartDate': order[8],
            'EndDate': order[9],
            'MachineCodeFrom': order[10],
            'MachineCodeTo': order[11],
            'DeliveryDate': order[12],
            'ReturnDeliveryDate': order[13],
            'Postponed': bool(order[14]),
            'PostponedDays': order[15],
            'IsReturn': bool(order[16]),
            'DeliveryCost': order[17]
        }
        orders_list.append(order_dict)

    return JsonResponse(orders_list, safe=False)

@login_required
def change_order_status(request, order_id, status_id):
    if request.method == 'POST':
        try:

            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("""
                SELECT Id, StatusId, ChamberId FROM ORDER_ WHERE Id = ?
            """, (order_id,))
            order = cursor.fetchone()

            if order is None:

                conn.close()
                return JsonResponse({'error': 'Order not found'}, status=404)

            order_chamber_id = order[2]


            cursor.execute("""
                UPDATE ORDER_ SET StatusId = ? WHERE Id = ?
            """, (status_id, order_id))




            if status_id == 3:
                cursor.execute("""
                    SELECT ChamberId FROM ORDER_CHAMBER WHERE OrderId = ?
                """, (order_id,))
                order_chamber = cursor.fetchone()

                if order_chamber is not None:
                    new_chamber_id = order_chamber[0]


                    cursor.execute("""
                        UPDATE ORDER_ SET ChamberId = ? WHERE Id = ?
                    """, (new_chamber_id, order_id))


                    cursor.execute("""
                        DELETE FROM ORDER_CHAMBER WHERE OrderId = ? AND ChamberId = ?
                    """, (order_id, new_chamber_id))


                    cursor.execute("""
                        UPDATE CHAMBER SET Status = 0 WHERE Id = ?
                    """, (order_chamber_id,))


            elif status_id == 6:

                cursor.execute("""
                    UPDATE ORDER_ SET DeliveryDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))


            elif status_id == 7:

                cursor.execute("""
                    UPDATE ORDER_ SET EndDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))


            elif status_id == 8:

                cursor.execute("""
                    UPDATE ORDER_ SET IsReturn = 1 WHERE Id = ?
                """, (order_id,))


            elif status_id == 9:
                

                cursor.execute("SELECT MachineIdFrom FROM ORDER_ WHERE Id = ?", (order_id,))
                order_info = cursor.fetchone()

                if order_info is None:
                    conn.close()
                    return JsonResponse({'error': 'Order information not found'}, status=404)
                
                machine_id_from = order_info[0]


                cursor.execute("SELECT Size FROM CHAMBER WHERE Id = ?", (order_chamber_id,))
                chamber_info = cursor.fetchone()

                if chamber_info is None:
                    conn.close()
                    return JsonResponse({'error': 'Chamber size not found'}, status=404)

                chamber_size = chamber_info[0]


                def find_available_chamber(machine_id, size):

                    cursor.execute("""
                        SELECT CHAMBER.Id
                        FROM CHAMBER
                        WHERE CHAMBER.MachineId = ? AND CHAMBER.Size = ? AND CHAMBER.Status = 0
                        LIMIT 1
                    """, (machine_id, size))
                    chamber = cursor.fetchone()

                    if chamber is None:

                        cursor.execute("""
                            SELECT C.Id, M1.Id AS OriginalMachineId
                            FROM MACHINE M1
                            JOIN MACHINE M2 ON M1.Address = M2.Address 
                                AND M1.PostalCode = M2.PostalCode 
                                AND M1.Location = M2.Location
                            JOIN CHAMBER C ON M2.Id = C.MachineId
                            WHERE M1.Id = ? AND C.Size = ? AND C.Status = 0
                            LIMIT 1
                        """, (machine_id, size))
                        alternate_chamber = cursor.fetchone()

                        if alternate_chamber is not None:
                            return alternate_chamber[0], machine_id
                        else:
                            return None, None
                    else:
                        return chamber[0], machine_id


                available_chamber_id, _ = find_available_chamber(machine_id_from, chamber_size)
                
                if available_chamber_id is None:
                    conn.close()
                    return JsonResponse({'error': 'No available chamber of the same size found'}, status=404)

                cursor.execute("""
                    UPDATE ORDER_ SET ChamberId = ? WHERE Id = ?
                """, (available_chamber_id, order_id))


                cursor.execute("""
                    UPDATE CHAMBER SET Status = 1 WHERE Id = ?
                """, (available_chamber_id,))


                cursor.execute("""
                    UPDATE CHAMBER SET Status = 0 WHERE Id = ?
                """, (order_chamber_id,))


            elif status_id == 10:

                cursor.execute("""
                    UPDATE ORDER_ SET ReturnDeliveryDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))


            elif status_id == 11:

                cursor.execute("""
                    UPDATE ORDER_ SET EndDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))

                cursor.execute("""
                    UPDATE CHAMBER SET Status = 0 WHERE Id = ?
                """, (order_chamber_id,))    


            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Order status updated successfully'})

        except Exception as e:

            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def update_order_status_by_chamber(request, chamber_id):
    if request.method == 'POST':
        try:

            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("""
                SELECT Id, StatusId FROM ORDER_ 
                WHERE ChamberId = ? AND Active = 1 AND StatusId IN (1, 2, 5, 6, 8, 9, 10)
            """, (chamber_id,))
            order = cursor.fetchone()

            if order is None:

                conn.close()
                return JsonResponse({'error': 'No active order found with the specified status for this chamber'}, status=404)

            order_id, current_status_id = order


            new_status_id = current_status_id + 1
            cursor.execute("""
                UPDATE ORDER_ SET StatusId = ? WHERE Id = ?
            """, (new_status_id, order_id))




            if new_status_id == 3:
                cursor.execute("""
                    SELECT ChamberId FROM ORDER_CHAMBER WHERE OrderId = ?
                """, (order_id,))
                order_chamber = cursor.fetchone()

                if order_chamber is not None:
                    new_chamber_id = order_chamber[0]


                    cursor.execute("""
                        UPDATE ORDER_ SET ChamberId = ? WHERE Id = ?
                    """, (new_chamber_id, order_id))


                    cursor.execute("""
                        DELETE FROM ORDER_CHAMBER WHERE OrderId = ? AND ChamberId = ?
                    """, (order_id, new_chamber_id))

                    cursor.execute("""
                        UPDATE CHAMBER SET Status = 0 WHERE Id = ?
                    """, (chamber_id,))


            elif new_status_id == 6:

                cursor.execute("""
                    UPDATE ORDER_ SET DeliveryDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))


            elif new_status_id == 7:

                cursor.execute("""
                    UPDATE ORDER_ SET EndDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))


            elif new_status_id == 8:

                cursor.execute("""
                    UPDATE ORDER_ SET IsReturn = 1 WHERE Id = ?
                """, (order_id,))


            elif new_status_id == 9:


                cursor.execute("SELECT MachineIdFrom FROM ORDER_ WHERE Id = ?", (order_id,))
                order_info = cursor.fetchone()

                if order_info is None:
                    conn.close()
                    return JsonResponse({'error': 'Order information not found'}, status=404)
                
                machine_id_from = order_info[0]
            

                cursor.execute("SELECT Size FROM CHAMBER WHERE Id = ?", (chamber_id,))
                chamber_info = cursor.fetchone()

                if chamber_info is None:
                    conn.close()
                    return JsonResponse({'error': 'Chamber size not found'}, status=404)

                chamber_size = chamber_info[0]


                def find_available_chamber_of_same_size(machine_id, size):

                    cursor.execute("""
                        SELECT CHAMBER.Id
                        FROM CHAMBER
                        WHERE CHAMBER.MachineId = ? AND CHAMBER.Size = ? AND CHAMBER.Status = 0
                        LIMIT 1
                    """, (machine_id, size))
                    chamber = cursor.fetchone()

                    if chamber is None:

                        cursor.execute("""
                            SELECT C.Id, M1.Id AS OriginalMachineId
                            FROM MACHINE M1
                            JOIN MACHINE M2 ON M1.Address = M2.Address 
                                AND M1.PostalCode = M2.PostalCode 
                                AND M1.Location = M2.Location
                            JOIN CHAMBER C ON M2.Id = C.MachineId
                            WHERE M1.Id = ? AND C.Size = ? AND C.Status = 0
                            LIMIT 1
                        """, (machine_id, size))
                        alternate_chamber = cursor.fetchone()

                        if alternate_chamber is not None:
                            return alternate_chamber[0], machine_id
                        else:
                            return None, None
                    else:
                        return chamber[0], machine_id


                available_chamber_id, _ = find_available_chamber_of_same_size(machine_id_from, chamber_size)
                
                if available_chamber_id is None:
                    conn.close()
                    return JsonResponse({'error': 'No available chamber of the same size found'}, status=404)

                cursor.execute("""
                    UPDATE ORDER_ SET ChamberId = ? WHERE Id = ?
                """, (available_chamber_id, order_id))


                cursor.execute("""
                    UPDATE CHAMBER SET Status = 1 WHERE Id = ?
                """, (available_chamber_id,))


                cursor.execute("""
                    UPDATE CHAMBER SET Status = 0 WHERE Id = ?
                """, (chamber_id,))


            elif new_status_id == 10:

                cursor.execute("""
                    UPDATE ORDER_ SET ReturnDeliveryDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))


            elif new_status_id == 11:

                cursor.execute("""
                    UPDATE ORDER_ SET EndDate = ? WHERE Id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))

                cursor.execute("""
                    UPDATE CHAMBER SET Status = 0 WHERE Id = ?
                """, (chamber_id,))


            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Order status updated successfully'})

        except Exception as e:

            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def postpone_order(request):
    if request.method == 'PUT':
        try:

            data = json.loads(request.body)
            order_id = data.get('OrderId')
            postponed_days = data.get('PostponedDays')

            if order_id is None or postponed_days is None:
                return JsonResponse({'error': 'OrderId and PostponedDays are required'}, status=400)


            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()


            cursor.execute("""
                SELECT Id FROM ORDER_ 
                WHERE Id = ? AND Active = 1 AND StatusId <= 5
            """, (order_id,))
            order_exists = cursor.fetchone()

            if order_exists is None or postponed_days >=7:
                conn.close()
                return JsonResponse({'error': 'Order not found or not eligible for postponement'}, status=404)


            cursor.execute("""
                UPDATE ORDER_ 
                SET Postponed = 1, PostponedDays = ? 
                WHERE Id = ?
            """, (postponed_days, order_id))


            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Order postponed successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


