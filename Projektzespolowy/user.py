from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required
from .coordinates import get_coordinates

@login_required
def get_all_users(request):
    
    
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    
    cursor.execute("SELECT * FROM USER")

    
    users = cursor.fetchall()

    
    conn.close()

    
    users_list = []
    for user in users:
        user_dict = {
            'Id': user[0],
            'Mail': user[1],
            'Password': user[2],
            'Active': bool(user[3])
        }
        users_list.append(user_dict)

    
    return JsonResponse(users_list, safe=False)

@login_required
def disable_user(request):
    if request.method == 'PUT':
        # Pobranie danych z żądania
        data = json.loads(request.body)
        user_id = data.get('Id')

        # Połączenie z bazą danych
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        try:
            # Aktualizacja rekordu w tabeli USER
            cursor.execute("""
            UPDATE USER
            SET Active = 0
            WHERE Id = ?;
            """, (user_id,))

            # Zatwierdzenie zmian w bazie danych
            conn.commit()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON informującej o sukcesie
            return JsonResponse({'success': True, 'message': 'Pomyślnie zdezaktywowano użytkownika.'}, status=200)
        except Exception as e:
            # Jeśli wystąpił błąd, wycofaj zmiany w bazie danych
            conn.rollback()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON z informacją o błędzie
            return JsonResponse({'success': False, 'message': f'Błąd podczas dezaktywacji użytkownika: {str(e)}'}, status=500)

    # Zwrócenie odpowiedzi JSON w przypadku żądania innego niż PUT
    return JsonResponse({'error': 'Metoda nieobsługiwana lub brak uprawnień.'}, status=405)

@login_required
def enable_user(request):
    if request.method == 'PUT':
        # Pobranie danych z żądania
        data = json.loads(request.body)
        user_id = data.get('Id')

        # Połączenie z bazą danych
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        try:
            # Aktualizacja rekordu w tabeli USER
            cursor.execute("""
            UPDATE USER
            SET Active = 1
            WHERE Id = ?;
            """, (user_id,))

            # Zatwierdzenie zmian w bazie danych
            conn.commit()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON informującej o sukcesie
            return JsonResponse({'success': True, 'message': 'Pomyślnie aktywowano użytkownika.'}, status=200)
        except Exception as e:
            # Jeśli wystąpił błąd, wycofaj zmiany w bazie danych
            conn.rollback()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON z informacją o błędzie
            return JsonResponse({'success': False, 'message': f'Błąd podczas aktywacji użytkownika: {str(e)}'}, status=500)

    # Zwrócenie odpowiedzi JSON w przypadku żądania innego niż PUT
    return JsonResponse({'error': 'Metoda nieobsługiwana lub brak uprawnień.'}, status=405)


@login_required
def get_user_by_id(request, user_id):
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT USER.Id, 
        USER.Mail, 
        USER.Password, 
        USER.Active, 
        PERSONAL_DATA.FirstName, 
        PERSONAL_DATA.LastName, 
        PERSONAL_DATA.BirthDate, 
        PERSONAL_DATA.Sex, 
        PERSONAL_DATA.DefaultAddress, 
        PERSONAL_DATA.DefaultPostalcode, 
        PERSONAL_DATA.DefaultLocation, 
        PERSONAL_DATA.Phone, 
        PERSONAL_DATA.Country,
        PERSONAL_DATA.Latitude,
        PERSONAL_DATA.Longitude           
    FROM USER 
    LEFT JOIN PERSONAL_DATA 
    ON USER.Id = PERSONAL_DATA.UserId 
    WHERE USER.Id = ?''', (user_id,))
    
    user_data = cursor.fetchone()

    conn.close()

    if user_data:
        user_dict = {
            'Id': user_data[0],
            'Mail': user_data[1],
            'Password': user_data[2],
            'Active': bool(user_data[3]),
            'FirstName': user_data[4],
            'LastName': user_data[5],
            'BirthDate': user_data[6],
            'Sex': bool(user_data[7]),
            'DefaultAddress': user_data[8],
            'DefaultPostalcode': user_data[9],
            'DefaultLocation': user_data[10],
            'Phone': user_data[11],
            'Country': user_data[12],
            'Latitude': user_data[13],
            'Longitude': user_data[14]
        }
        return JsonResponse(user_dict)
    else:
        return JsonResponse({'error': 'User not found'}, status=404)

@login_required
def edit_user(request, user_id):
    if request.method == 'PUT':
        try:
            # Parsuj dane JSON z ciała żądania
            data = json.loads(request.body)

            # Ustaw dane użytkownika do aktualizacji
            user_updated_data = {
                'Mail': data.get('Mail'),
                'Password': data.get('Password'),
                'Active': data.get('Active')
            }

            # Ustaw dane osobowe użytkownika do aktualizacji
            personal_updated_data = {
                'FirstName': data.get('FirstName'),
                'LastName': data.get('LastName'),
                'BirthDate': data.get('BirthDate'),
                'Sex': data.get('Sex'),
                'DefaultAddress': data.get('DefaultAddress'),
                'DefaultPostalcode': data.get('DefaultPostalcode'),
                'DefaultLocation': data.get('DefaultLocation'),
                'Phone': data.get('Phone'),
                'Country': data.get('Country', 'Poland')  # Domyślnie Poland, jeśli brak wartości
            }

            # Sprawdź, czy adres został zmieniony
            address_changed = (
                data.get('DefaultAddress') or 
                data.get('DefaultLocation')
            )

            # Połącz się z bazą danych
            conn = sqlite3.connect('msbox_database.db')
            cursor = conn.cursor()

            # Rozpocznij transakcję
            conn.execute("BEGIN")

            try:
                # Aktualizuj dane użytkownika w tabeli USER
                user_update_query = """
                    UPDATE USER SET 
                        Mail = ?, 
                        Password = ?, 
                        Active = ?
                    WHERE Id = ?
                """
                cursor.execute(user_update_query, (
                    user_updated_data['Mail'],
                    user_updated_data['Password'],
                    user_updated_data['Active'],
                    user_id
                ))

                # Jeśli adres się zmienił, zaktualizuj koordynaty
                if address_changed:
                    default_address = data.get('DefaultAddress')
                    default_location = data.get('DefaultLocation')
                    latitude, longitude = get_coordinates(default_address, default_location)

                    if latitude is None or longitude is None:
                        return JsonResponse({'error': 'Failed to obtain coordinates for the given address'}, status=400)

                    personal_updated_data['Latitude'] = latitude
                    personal_updated_data['Longitude'] = longitude

                # Aktualizuj dane osobowe użytkownika w tabeli PERSONAL_DATA
                personal_update_query = """
                    UPDATE PERSONAL_DATA SET 
                        FirstName = ?, 
                        LastName = ?, 
                        BirthDate = ?, 
                        Sex = ?, 
                        DefaultAddress = ?, 
                        DefaultPostalcode = ?, 
                        DefaultLocation = ?, 
                        Phone = ?, 
                        Country = ?,
                        Latitude = ?, 
                        Longitude = ?
                    WHERE UserId = ?
                """
                cursor.execute(personal_update_query, (
                    personal_updated_data['FirstName'],
                    personal_updated_data['LastName'],
                    personal_updated_data['BirthDate'],
                    personal_updated_data['Sex'],
                    personal_updated_data['DefaultAddress'],
                    personal_updated_data['DefaultPostalcode'],
                    personal_updated_data['DefaultLocation'],
                    personal_updated_data['Phone'],
                    personal_updated_data['Country'],
                    personal_updated_data.get('Latitude'),  # Wartość może być None
                    personal_updated_data.get('Longitude'),  # Wartość może być None
                    user_id
                ))

                # Zatwierdź transakcję
                conn.commit()

            except Exception as e:
                # W przypadku błędu, cofnij transakcję
                conn.rollback()
                raise e

            finally:
                # Zamknij połączenie z bazą danych
                conn.close()

            return JsonResponse({'message': 'User data updated successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)