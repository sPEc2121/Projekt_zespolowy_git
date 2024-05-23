from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required
from .coordinates import get_coordinates

@login_required
def get_all_statuses(request):
    if request.method == 'GET':
        try:
            # Połącz się z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Pobierz wszystkie statusy z tabeli STATUS
            cursor.execute("""
                SELECT Id, StatusName FROM STATUS
            """)
            statuses = cursor.fetchall()

            # Zamknij połączenie z bazą danych
            conn.close()

            # Jeśli znaleziono statusy, zwróć je jako listę słowników
            if statuses:
                status_list = [{'Id': status[0], 'StatusName': status[1]} for status in statuses]
                return JsonResponse(status_list, safe=False)
            else:
                # Jeśli nie znaleziono statusów, zwróć pustą listę
                return JsonResponse([], safe=False)

        except Exception as e:
            # W przypadku błędu zwróć odpowiedni komunikat
            return JsonResponse({'error': str(e)}, status=500)

    else:
        # Jeśli metoda żądania nie jest GET, zwróć odpowiedni komunikat
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@login_required
def update_order(request):
    if request.method == 'PUT':
        try:
            # Pobranie danych z żądania
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

            # Połączenie z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Znalezienie odpowiednich Id na podstawie nazw i adresów e-mail
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

            # Rozpoczęcie transakcji
            conn.execute("BEGIN")

            # Aktualizacja rekordu w tabeli ORDER_
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

            # Zatwierdzenie zmian w bazie danych
            conn.commit()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON informującej o sukcesie
            return JsonResponse({'success': True, 'message': 'Order updated successfully.'}, status=200)

        except Exception as e:
            # Jeśli wystąpił błąd, wycofaj zmiany w bazie danych
            conn.rollback()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON z informacją o błędzie
            return JsonResponse({'success': False, 'message': f'Error updating order: {str(e)}'}, status=500)

    # Zwrócenie odpowiedzi JSON w przypadku żądania innego niż PUT
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def update_machine(request):
    if request.method == 'POST':
        try:
            # Pobranie danych z żądania
            data = json.loads(request.body)
            machine_id = data.get('Id')
            address = data.get('Address')
            postal_code = data.get('PostalCode')
            location = data.get('Location')

            # Generowanie koordynatów na podstawie adresu maszyny
            latitude, longitude = get_coordinates(address, location)

            if latitude is None or longitude is None:
                return JsonResponse({'error': 'Failed to obtain coordinates for the given address'}, status=400)

            # Połączenie z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Sprawdzenie, czy maszyna o podanym Id istnieje
            cursor.execute("""
                SELECT Id FROM MACHINE WHERE Id = ?
            """, (machine_id,))
            machine_exists = cursor.fetchone()

            if machine_exists is None:
                # Maszyna o podanym Id nie istnieje - zwróć błąd
                conn.close()
                return JsonResponse({'error': 'Machine not found'}, status=404)

            # Aktualizacja danych maszyny
            cursor.execute("""
                UPDATE MACHINE
                SET Address = ?, PostalCode = ?, Location = ?, Latitude = ?, Longitude = ?
                WHERE Id = ?
            """, (address, postal_code, location, latitude, longitude, machine_id))

            # Zatwierdzenie zmian w bazie danych
            conn.commit()
            conn.close()

            return JsonResponse({'message': 'Machine updated successfully'}, status=200)

        except Exception as e:
            # Wystąpił błąd - wykonaj rollback
            conn.rollback()
            conn.close()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)