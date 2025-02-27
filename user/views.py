from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse


from .models import CustomUser
from .roles import Role

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
                messages.error(request, 'Invalid role.')
                return redirect('login')

        messages.error(request, 'Invalid email or password.')
        return redirect('login')

    elif request.method == 'GET':
        if 'role' in request.GET and request.GET['role'] == 'admin':
            return render(request, 'admin_login.html')

        return render(request, 'login.hviews.login_viewtml')

    # ✅ Handle unsupported HTTP methods explicitly
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

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
            # return redirect('dashboard')
        except Role.DoesNotExist:
            messages.error(request, 'Invalid role specified.')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'add_user.html')
