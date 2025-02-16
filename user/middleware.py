# user/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from jwt import decode, InvalidTokenError
from django.conf import settings

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude login and token refresh paths from authentication
        excluded_paths = [reverse('login'), reverse('token_refresh')]
        if request.path in excluded_paths:
            return self.get_response(request)

        access_token = request.COOKIES.get('access_token')
        
        if not access_token:
            return redirect('login')

        try:
            # Decode the token
            decoded_token = decode(access_token, settings.SIMPLE_JWT['SIGNING_KEY'], algorithms=['HS256'])
            user_id = decoded_token['user_id']
            
            # Get the user
            User = get_user_model()
            request.user = User.objects.get(id=user_id)
            
        except (InvalidTokenError, User.DoesNotExist):
            return redirect('login')

        return self.get_response(request)