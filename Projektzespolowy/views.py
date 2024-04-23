from django.http import JsonResponse
import json
import sqlite3
from django.views.decorators.csrf import csrf_exempt

def get_all_users(request):
    # Połączenie z bazą danych
    conn = sqlite3.connect('msbox_database.db')
    cursor = conn.cursor()

    # Wykonanie zapytania SELECT
    cursor.execute("SELECT * FROM USER")

    # Pobranie wszystkich wyników
    users = cursor.fetchall()

    # Zamknięcie połączenia
    conn.close()

    # Konwersja wyników na listę słowników
    users_list = []
    for user in users:
        user_dict = {
            'Id': user[0],
            'Mail': user[1],
            'Password': user[2],
            'Active': bool(user[3])
        }
        users_list.append(user_dict)

    # Zwrócenie danych w formacie JSON
    return JsonResponse(users_list, safe=False)

@csrf_exempt
def login(request):
    if request.method == 'POST':
        # Odczytanie danych z ciała żądania
        data = json.loads(request.body)
        mail = data.get('Mail')
        password = data.get('Password')

        # Połączenie z bazą danych
        conn = sqlite3.connect('msbox_database.db')
        cursor = conn.cursor()

        # Sprawdzenie czy istnieje użytkownik o podanym mailu i haśle oraz czy konto jest aktywne
        cursor.execute("SELECT * FROM USER WHERE Mail=? AND Password=? AND Active=1", (mail, password))
        user = cursor.fetchone()

        # Zamknięcie połączenia
        conn.close()

        # Jeśli użytkownik istnieje i konto jest aktywne
        if user:
            response_data = {'token': 'token123'}
            return JsonResponse(response_data)
        else:
            # Jeśli użytkownik nie istnieje lub konto nie jest aktywne
            return JsonResponse({}, status=400)
    else:
        # Obsługa przypadku, gdy żądanie nie jest metodą POST
        return JsonResponse({'error': 'Method not allowed'}, status=405)
