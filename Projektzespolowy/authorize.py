from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta

def register(request):
    if request.method == 'POST':
        # Pobranie danych z żądania
        data = json.loads(request.body)
        mail = data.get('Mail')
        password = data.get('Password')
        first_name = data.get('FirstName')
        last_name = data.get('LastName')
        birth_date = data.get('BirthDate')
        sex = data.get('Sex')
        default_address = data.get('DefaultAddress')
        default_postalcode = data.get('DefaultPostalcode')
        default_location = data.get('DefaultLocation')
        phone = data.get('Phone')
        country = 'Poland' # Ustaw domyślną wartość Polska, jeśli nie zostanie przekazana

        # Połączenie z bazą danych
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        try:
            # Wstawienie danych do tabeli USER
            cursor.execute("""
            INSERT INTO USER (Mail, Password, Active)
            VALUES (?, ?, 1);
            """, (mail, password))

            # Pobranie ID użytkownika
            user_id = cursor.lastrowid

            # Wstawienie danych do tabeli PERSONAL_DATA
            cursor.execute("""
            INSERT INTO PERSONAL_DATA (UserId, FirstName, LastName, BirthDate, Sex, DefaultAddress, DefaultPostalcode, DefaultLocation, Phone, Country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (user_id, first_name, last_name, birth_date, sex, default_address, default_postalcode, default_location, phone, country))

            # Wstawienie danych do tabeli USER_ROLE
            cursor.execute("""
            INSERT INTO USER_ROLE (UserId, RoleId)
            VALUES (?, ?);
            """, (user_id, 1))  # Przypisanie roli o ID=1

            # Zatwierdzenie zmian w bazie danych
            conn.commit()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON informującej o sukcesie
            return JsonResponse({'success': True, 'message': 'Rejestracja zakończona pomyślnie.'}, status=201)
        except Exception as e:
            # Jeśli wystąpił błąd, wycofaj zmiany w bazie danych
            conn.rollback()

            # Zamknięcie połączenia z bazą danych
            conn.close()

            # Zwrócenie odpowiedzi JSON z informacją o błędzie
            return JsonResponse({'success': False, 'message': f'Błąd podczas rejestracji: {str(e)}'}, status=500)

    # Zwrócenie odpowiedzi JSON w przypadku żądania innego niż POST
    return JsonResponse({'error': 'Metoda nieobsługiwana.'}, status=405)


def login(request):
    if request.method == 'POST':
        
        data = json.loads(request.body)
        mail = data.get('Mail')
        password = data.get('Password')

        
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        
        cursor.execute('''SELECT u.*, r.RoleName 
                       FROM USER u
                       INNER JOIN USER_ROLE ur on u.Id = ur.UserId
                       INNER JOIN ROLE r on ur.RoleId = r.Id
                       WHERE Mail=? AND Password=? AND Active=1''', (mail, password))
        user = cursor.fetchone()

        
        conn.close()

        
        if user is not None:
            
            payload = {'Id': user[0],'Mail': mail, 'RoleName': user[4]}  # Assuming RoleId is at index 6
            secret_key = 'WSPA i tak tego nikt nie przeczyta'

            expiration_time = datetime.utcnow() + timedelta(hours=2)
            payload['exp'] = expiration_time

            token = jwt.encode(payload, secret_key, algorithm='HS256')

            response_data = {'jwt_token': token}
            return JsonResponse(response_data)
        else:
            
            return JsonResponse({}, status=400)
    else:
        
        return JsonResponse({'error': 'Method not allowed'}, status=405)