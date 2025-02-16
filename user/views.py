# user/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse
from .models import CustomUser
from .roles import Role
from datetime import datetime, timedelta
from rest_framework_simplejwt.tokens import RefreshToken

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.role.name in ["admin", "user"]:
                login(request, user)
                # Generate tokens
                tokens = user.tokens()
                
                response = redirect('dashboard')
                
                # Set tokens in cookies
                response.set_cookie(
                    key='refresh_token',
                    value=tokens['refresh'],
                    httponly=True,
                    samesite='Lax',
                    secure=True,
                    max_age=24*60*60  # 1 day
                )
                response.set_cookie(
                    key='access_token',
                    value=tokens['access'],
                    httponly=True,
                    samesite='Lax',
                    secure=True,
                    max_age=15*60  # 15 minutes
                )
                
                return response
            else:
                messages.error(request, 'Invalid role.')
                return redirect('login')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    if request.method == 'GET':
        if 'role' in request.GET and request.GET['role'] == 'admin':
            return render(request, 'admin_login.html')
        return render(request, 'login.html')

def refresh_token_view(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        return redirect('login')

    try:
        refresh = RefreshToken(refresh_token)
        tokens = {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }

        response = redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        response.set_cookie(
            key='access_token',
            value=tokens['access'],
            httponly=True,
            samesite='Lax',
            secure=True,
            max_age=15*60  # 15 minutes
        )
        response.set_cookie(
            key='refresh_token',
            value=tokens['refresh'],
            httponly=True,
            samesite='Lax',
            secure=True,
            max_age=24*60*60  # 1 day
        )

        return response

    except Exception as e:
        return redirect('login')
    
@login_required
def logout(request):
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        response = redirect('login')
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response
    except Exception:
        return redirect('login')
@login_required
def dashboard(request):
    return render(request, 'content.html')
@login_required
def add_user_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role_name = request.POST.get('role')

        try:
            role = Role.objects.get(name=role_name)
            new_user = CustomUser(
                username=username,
                email=email,
                role=role
            )
            new_user.set_password(password)
            new_user.save()
            messages.success(request, 'User added successfully!')
            return redirect('dashboard')
        except Role.DoesNotExist:
            messages.error(request, 'Invalid role specified.')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'add_user.html')