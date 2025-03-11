from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseNotAllowed
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from .models import CustomUser
from .roles import Role
import json


@csrf_exempt
def validate_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            field = data.get("field")
            value = data.get("value")

            if not field or not value:
                return JsonResponse({"error": "Field and value are required"}, status=400)

            if field == "username":
                exists = CustomUser.objects.filter(username=value).exists()
            elif field == "email":
                exists = CustomUser.objects.filter(email=value).exists()
            else:
                return JsonResponse({"error": "Invalid field"}, status=400)

            return JsonResponse({"exists": exists, "field": field})
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')  # Get checkbox value

        print(f"Remember Me Value: {remember_me}")  # Debugging statement

        if not email or not password:
            messages.error(request, "Email and password are required.", extra_tags="login")
            return redirect('login')

        user = authenticate(request, username=email, password=password)
        if user:
            if user.role.name in ["admin", "user"]:
                login(request, user)

                # Check if "Remember Me" is being processed
                if remember_me:
                    print("Setting session expiry to 2 weeks")
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    print("Setting session expiry to browser close")
                    request.session.set_expiry(0)  # Session expires when the browser is closed

                # Check if session expiry is actually set
                print(f"Session expiry is: {request.session.get_expiry_age()} seconds")

                return redirect('dashboard')

            messages.error(request, "Invalid role.", extra_tags="login")
        else:
            messages.error(request, "Invalid email or password.", extra_tags="login")

        return redirect('login')

    elif request.method == 'GET':
        return render(request, 'user/login.html')

    return HttpResponseNotAllowed(['GET', 'POST'])

# from datetime import timedelta

# @csrf_exempt
# def login_view(request):
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         remember_me = request.POST.get('remember-me')  # Get the "Remember Me" value

#         if not email or not password:
#             messages.error(request, "Email and password are required.", extra_tags="login")
#             return redirect('login')

#         user = authenticate(request, username=email, password=password)
#         if user:
#             if user.role.name in ["admin", "user"]:
#                 login(request, user)

#                 # If "Remember Me" is selected, set session expiry to 1 week
#                 if remember_me:
#                     request.session.set_expiry(timedelta(weeks=1))  # Set session to 1 week
#                 else:
#                     request.session.set_expiry(0)  # Session expires when the browser is closed

#                 return redirect('dashboard')
#             messages.error(request, "Invalid role.", extra_tags="login")
#             return redirect('login')

#         messages.error(request, "Invalid email or password.", extra_tags="login")
#         return redirect('login')


#     return HttpResponseNotAllowed(['GET', 'POST'])



@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    return render(request, 'user/dashboard.html')


@login_required
def add_user_view(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role_name = request.POST.get('role')

        # Check if all fields are provided
        if not all([first_name, last_name, username, email, password, role_name]):
            messages.error(request, "All fields are required.", extra_tags="add_user")
            return render(request, 'user/add_user.html')

        # Check for existing username and email
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.", extra_tags="add_user")
            return render(request, 'user/add_user.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken.", extra_tags="add_user")
            return render(request, 'usser/add_user.html')

        try:
            # Get the role
            role = Role.objects.get(name=role_name)
            
            # Create the new user
            new_user = CustomUser(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                role=role
            )
            new_user.set_password(password)
            new_user.save()

            messages.success(request, "User added successfully!", extra_tags="add_user")

        except Role.DoesNotExist:
            messages.error(request, "Invalid role specified.", extra_tags="add_user")
        except IntegrityError as e:
            messages.error(request, f"Database error: {e}", extra_tags="add_user")
        except ValidationError as e:
            messages.error(request, f"Validation error: {e}", extra_tags="add_user")
        except Exception as e:
            messages.error(request, f"Unexpected error: {e}", extra_tags="add_user")

    return render(request, 'user/add_user.html')

@login_required
def users_list_view(request):
    users = CustomUser.objects.all()
    return render(request, 'user/users_list.html', {'users': users})


@login_required
def delete_user(request, user_id):
    if request.method == "POST":
        try:
            user = CustomUser.objects.get(id=user_id)
            user.delete()
            messages.success(request, "User deleted successfully.", extra_tags="users_list")
        except CustomUser.DoesNotExist:
            messages.error(request, "User not found.", extra_tags="users_list")
        return redirect('users_list')

    return HttpResponseNotAllowed(['POST'])

@login_required
def edit_user_view(request, user_id):
    if request.method == 'POST':
        try:
            user = CustomUser.objects.get(id=user_id)
            username = request.POST.get('username')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            role_name = request.POST.get('role')

            # Only update username, first_name, last_name, and role
            user.username = username
            user.first_name = first_name
            user.last_name = last_name

            # Role validation
            role = Role.objects.get(name=role_name)
            user.role = role

            user.save()

            messages.success(request, "User updated successfully!", extra_tags="users_list")
        except CustomUser.DoesNotExist:
            messages.error(request, "User not found.", extra_tags="users_list")
        except Role.DoesNotExist:
            messages.error(request, "Invalid role.", extra_tags="users_list")
        except Exception as e:
            messages.error(request, f"Error: {e}", extra_tags="users_list")

    return redirect('users_list')
