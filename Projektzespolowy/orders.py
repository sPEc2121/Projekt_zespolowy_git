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
        # Otrzymujemy dane z ciała żądania jako słownik
        order_data = json.loads(request.body)
        # Pobieramy wartości ze słownika
        sender_mail = order_data.get('SenderMail')
        receiver_mail = order_data.get('ReceiverMail')
        payment_method_id = order_data.get('PaymentMethodId')
        description = order_data.get('Description')
        machine_id_from = order_data.get('MachineIdFrom')
        machine_id_to = order_data.get('MachineIdTo')
        size = order_data.get('Size')

        # Ustawiamy domyślne wartości
        status_id = 1  # Domyślnie ustawiamy na 1
        active = 1     # Domyślnie ustawiamy na 1
        start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Bieżąca data i czas
        is_return = 0

        # Połącz się z bazą danych
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        # Rozpocznij transakcję
        conn.execute("BEGIN")

        # Znajdź identyfikator sendera na podstawie maila
        cursor.execute("SELECT Id FROM USER WHERE Mail = ?", (sender_mail,))
        sender_id = cursor.fetchone()
        if sender_id is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'Sender not found'}, status=404)
        sender_id = sender_id[0]

        # Znajdź identyfikator receivera na podstawie maila
        cursor.execute("SELECT Id FROM USER WHERE Mail = ?", (receiver_mail,))
        receiver_id = cursor.fetchone()
        if receiver_id is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'Receiver not found'}, status=404)
        receiver_id = receiver_id[0]

        def find_available_chamber(machine_id, size):
            # Szukaj wolnej komory dla podanej maszyny
            cursor.execute("""
                SELECT CHAMBER.Id
                FROM CHAMBER
                WHERE CHAMBER.MachineId = ? AND CHAMBER.Size = ? AND CHAMBER.Status = 0
                LIMIT 1
            """, (machine_id, size))
            chamber = cursor.fetchone()

            if chamber is None:
                # Jeśli nie znaleziono wolnej komory, sprawdź inne maszyny o tym samym adresie
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
                    return alternate_chamber[0], machine_id  # Zwraca id komory i oryginalne id maszyny
                else:
                    return None, None
            else:
                return chamber[0], machine_id

        # Znajdź wolną komorę dla machine_id_from
        chamber_id_from, valid_machine_id_from = find_available_chamber(machine_id_from, size)
        if chamber_id_from is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'No available chamber found for the selected from machine and size'}, status=400)

        # Znajdź wolną komorę dla machine_id_to
        chamber_id_to, valid_machine_id_to = find_available_chamber(machine_id_to, size)
        if chamber_id_to is None:
            conn.rollback()
            conn.close()
            return JsonResponse({'error': 'No available chamber found for the selected to machine and size'}, status=400)

        # Wyznacz koszt dostawy na podstawie danych z tabeli CHAMBER_DETAILS
        cursor.execute("SELECT Price FROM CHAMBER_DETAILS WHERE ChamberId = ? AND Active = 1", (chamber_id_to,))
        chamber_details = cursor.fetchone()

        if chamber_details:
            delivery_cost = chamber_details[0] + 500  # Dodajemy 500 do ceny z CHAMBER_DETAILS
        else:
            delivery_cost = 0  # Jeśli brak danych, ustawiamy koszt na 0

        # Wstaw nowy rekord do tabeli ORDER_
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

        # Pobierz id utworzonego zamówienia
        order_id = cursor.lastrowid

        # Wstaw rekord do tabeli ORDER_CHAMBER
        cursor.execute("""
            INSERT INTO ORDER_CHAMBER (
                OrderId, 
                ChamberId
            ) VALUES (?, ?)
        """, (
            order_id,
            chamber_id_to
        ))

        # Zaktualizuj status komory na zajętą
        cursor.execute("""
            UPDATE CHAMBER
            SET Status = 1
            WHERE Id = ?
        """, (chamber_id_to,))

        # Zatwierdź transakcję
        conn.commit()
        conn.close()

        return JsonResponse({'message': 'Order created successfully'})

    except Exception as e:
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
            # Połącz się z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Sprawdź, czy istnieje zamówienie o podanym id
            cursor.execute("""
                SELECT Id, StatusId FROM ORDER_ WHERE Id = ?
            """, (order_id,))
            order = cursor.fetchone()
            print(order)
            if order is None:
                # Zamówienie o podanym id nie istnieje - zwróć błąd
                conn.close()
                return JsonResponse({'error': 'Order not found'}, status=404)

            current_status_id = order[1]

            # Zaktualizuj status zamówienia
            cursor.execute("""
                UPDATE ORDER_ SET StatusId = ? WHERE Id = ?
            """, (status_id, order_id))

            # Jeśli nowy status to 5, zaktualizuj ChamberId i usuń rekord z ORDER_CHAMBER
            if status_id == 5:
                cursor.execute("""
                    SELECT ChamberId FROM ORDER_CHAMBER WHERE OrderId = ?
                """, (order_id,))
                order_chamber = cursor.fetchone()

                if order_chamber is not None:
                    new_chamber_id = order_chamber[0]

                    # Zaktualizuj ChamberId w zamówieniu
                    cursor.execute("""
                        UPDATE ORDER_ SET ChamberId = ? WHERE Id = ?
                    """, (new_chamber_id, order_id))

                    # Usuń rekord z ORDER_CHAMBER
                    cursor.execute("""
                        DELETE FROM ORDER_CHAMBER WHERE OrderId = ? AND ChamberId = ?
                    """, (order_id, new_chamber_id))

            # Zatwierdź zmiany w bazie danych
            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Order status updated successfully'})

        except Exception as e:
            # Wystąpił błąd - wykonaj rollback
            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
  

def update_order_status_by_chamber(request, chamber_id):
    if request.method == 'POST':
        try:
            # Połącz się z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Sprawdź, czy istnieje aktywne zamówienie dla podanej komory z odpowiednim statusem
            cursor.execute("""
                SELECT Id, StatusId FROM ORDER_ 
                WHERE ChamberId = ? AND Active = 1 AND StatusId IN (1, 2, 5, 6, 8, 9, 10)
            """, (chamber_id,))
            order = cursor.fetchone()

            if order is None:
                # Nie znaleziono zamówienia spełniającego kryteria - zwróć błąd
                conn.close()
                return JsonResponse({'error': 'No active order found with the specified status for this chamber'}, status=404)

            order_id, current_status_id = order

            # Zaktualizuj status zamówienia na numer o 1 większy
            new_status_id = current_status_id + 1
            cursor.execute("""
                UPDATE ORDER_ SET StatusId = ? WHERE Id = ?
            """, (new_status_id, order_id))

            # Zatwierdź zmiany w bazie danych
            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Order status updated successfully'})

        except Exception as e:
            # Wystąpił błąd - wykonaj rollback
            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    


@login_required
def postpone_order(request):
    if request.method == 'PUT':
        try:
            # Parsuj dane JSON z ciała żądania
            data = json.loads(request.body)
            order_id = data.get('OrderId')
            postponed_days = data.get('PostponedDays')

            if order_id is None or postponed_days is None:
                return JsonResponse({'error': 'OrderId and PostponedDays are required'}, status=400)

            # Połącz się z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Sprawdź, czy zamówienie istnieje, jest aktywne i ma StatusId <= 5
            cursor.execute("""
                SELECT Id FROM ORDER_ 
                WHERE Id = ? AND Active = 1 AND StatusId <= 5
            """, (order_id,))
            order_exists = cursor.fetchone()

            if order_exists is None:
                conn.close()
                return JsonResponse({'error': 'Order not found or not eligible for postponement'}, status=404)

            # Aktualizuj kolumny Postponed i PostponedDays
            cursor.execute("""
                UPDATE ORDER_ 
                SET Postponed = 1, PostponedDays = ? 
                WHERE Id = ?
            """, (postponed_days, order_id))

            # Zatwierdź zmiany w bazie danych
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


