from django.http import JsonResponse
import json
import sqlite3
import jwt
from datetime import datetime, timedelta
from middlewares import login_required

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
