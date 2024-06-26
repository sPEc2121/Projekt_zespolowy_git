import jwt
from django.http import JsonResponse

def jwt_auth_middleware(get_response):
    def middleware(request):

        if request.path == '/login/' or request.path == '/register/' or '/update-order-status-by-chamber/<int:chamber_id>/':

            return get_response(request)

        if 'HTTP_AUTHORIZATION' in request.META:
            auth_header = request.META['HTTP_AUTHORIZATION']
            try:
                token = auth_header.split(' ')[1]

                decoded_token = jwt.decode(token, 'WSPA i tak tego nikt nie przeczyta', algorithms=['HS256'])
                request.user = decoded_token
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token has expired'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Invalid token'}, status=401)
        else:
            return JsonResponse({'error': 'Authorization header is missing'}, status=401)

        response = get_response(request)
        return response
    return middleware

def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if hasattr(request, 'user'):
            return view_func(request, *args, **kwargs)
        else:
            return JsonResponse({'error': 'Authorization required'}, status=401)
    return wrapper

