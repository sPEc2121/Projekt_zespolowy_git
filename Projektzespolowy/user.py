from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required

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

