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
    if request.method == 'POST':
        try:
            # Otrzymujemy dane z ciała żądania jako słownik
            order_data = json.loads(request.body)
            # Pobieramy wartości ze słownika
            sender_id = order_data.get('SenderId')
            receiver_id = order_data.get('ReceiverId')
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

            # Znajdź pierwszą wolną komorę o wybranym rozmiarze dla podanej maszyny
            cursor.execute("""
                SELECT 
                    CHAMBER.Id 
                FROM 
                    CHAMBER 
                WHERE 
                    CHAMBER.MachineId = ? AND 
                    CHAMBER.Size = ? AND 
                    CHAMBER.Status = 0 
                LIMIT 1
            """, (machine_id_to, size))
            chamber = cursor.fetchone()

            if chamber is not None:
                chamber_id = chamber[0]

                # Wyznacz koszt dostawy na podstawie danych z tabeli CHAMBER_DETAILS
                cursor.execute("""
                    SELECT 
                        Price 
                    FROM 
                        CHAMBER_DETAILS 
                    WHERE 
                        ChamberId = ? AND 
                        Active = 1
                """, (chamber_id,))
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
                    chamber_id,
                    payment_method_id,
                    description,
                    active,
                    start_date,
                    machine_id_from,
                    machine_id_to,
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
                    chamber_id
                ))

                # Zatwierdź transakcję
                conn.commit()
                conn.close()

                return JsonResponse({'message': 'Order created successfully'})

            else:
                # Nie znaleziono dostępnej komory - wykonaj rollback
                conn.rollback()
                conn.close()
                return JsonResponse({'error': 'No available chamber found for the selected machine and size'}, status=400)

        except Exception as e:
            # Wystąpił błąd - wykonaj rollback
            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    

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


