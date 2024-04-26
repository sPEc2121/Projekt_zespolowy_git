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
            """, (machine_id_from, size))
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