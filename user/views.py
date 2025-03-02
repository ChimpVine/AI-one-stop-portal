from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse
from .models import CustomUser
from .roles import Role
import json


@csrf_exempt
def validate_user(request):
    if request.method == "POST":
        data = json.loads(request.body)
        field = data.get("field")
        value = data.get("value")

        if field == "username":
            exists = CustomUser.objects.filter(username=value).exists()
        elif field == "email":
            exists = CustomUser.objects.filter(email=value).exists()
        else:
            return JsonResponse({"error": "Invalid field"}, status=400)

        return JsonResponse({"exists": exists, "field": field})

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
# def login_view(request):
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         password = request.POST.get('password')

#         user = authenticate(request, username=email, password=password)
#         if user is not None:
#             if user.role.name in ["admin", "user"]:
#                 login(request, user)
#                 return redirect('dashboard')
#             else:
#                 messages.error(request, 'Invalid role.')
#                 return redirect('login')
#         else:
#             messages.error(request, 'Invalid email or password.')
#             return redirect('login')

#     if request.method == 'GET':
#         if 'role' in request.GET and request.GET['role'] == 'admin':
#             return render(request, 'admin_login.html')
#         return render(request, 'login.html')


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.role.name in ["admin", "user"]:
                login(request, user)
                return redirect('dashboard')  # ✅ Redirect to dashboard if login is successful
            else:
                messages.error(request, 'Invalid role.', extra_tags="login")
                return redirect('login')

        messages.error(request, 'Invalid email or password.', extra_tags="login")
        return redirect('login')

    elif request.method == 'GET':
        if 'role' in request.GET and request.GET['role'] == 'admin':
            return render(request, 'admin_login.html')

        return render(request, 'login.html')

    # ✅ Handle unsupported HTTP methods explicitly
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')
from django.db import IntegrityError
from django.core.exceptions import ValidationError

@login_required
def add_user_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role_name = request.POST.get('role')

        # Validations before creating the user
        if not username or not email or not password or not role_name:
            messages.error(request, 'All fields are required.', extra_tags="add_user")
            return render(request, 'add_user.html')

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.', extra_tags="add_user")
            return render(request, 'add_user.html')

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email is already taken.', extra_tags="add_user")
            return render(request, 'add_user.html')

        try:
            role = Role.objects.get(name=role_name)
            
            # Create the new user
            new_user = CustomUser(
                username=username,
                email=email,
                role=role
            )
            new_user.set_password(password)
            new_user.save()

            messages.success(request, 'User added successfully!', extra_tags="add_user")
            return redirect('dashboard')

        except Role.DoesNotExist:
            messages.error(request, 'Invalid role specified.', extra_tags="add_user")
        except IntegrityError as e:
            messages.error(request, f"Database error: {str(e)}", extra_tags="add_user")
        except ValidationError as e:
            messages.error(request, f"Validation error: {str(e)}", extra_tags="add_user")
        except Exception as e:
            messages.error(request, f"Unexpected error: {e}", extra_tags="add_user")

    return render(request, 'add_user.html')
