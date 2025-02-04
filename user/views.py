from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import CustomUser
from .roles import Role  
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

def dashboard(request):
    return render(request, 'content.html')




@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, username=email, password=password)
        if user is not None:
            # Check the user's role and login accordingly
            if user.role.name == "admin":
                login(request, user)
                # messages.success(request, 'Welcome Admin!')
                return redirect('dashboard')  # Redirect to the  dashboard
            elif user.role.name == "user":
                login(request, user)
                # messages.success(request, 'Welcome User!')
                return redirect('dashboard')  # Redirect to the  dashboard
            else:
                messages.error(request, 'Invalid role.')
                return redirect('login')
        else:
            messages.error(request, 'Invalid email or password.')

    if request.method == 'GET':
        if 'role' in request.GET and request.GET['role'] == 'admin':
            return render(request, 'admin_login.html')  
        else:
            return render(request, 'login.html')  


from django.contrib import messages
from .models import CustomUser
from .roles import Role

def add_user_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role_name = request.POST.get('role')  # Get the role name from the form

        try:
            # Retrieve the Role object from the database
            role = Role.objects.get(name=role_name)

            # Create the user with the specified role
            new_user = CustomUser(
                username=username,
                email=email,
                password=password,
                role=role
            )
            new_user.set_password(password)
            new_user.save()
            # Display a success message
            messages.success(request, 'User added successfully!')
            return redirect('dashboard')  # Redirect to the desired page
        except Role.DoesNotExist:
            # If the role is not found in the database
            messages.error(request, 'Invalid role specified.')
        except Exception as e:
            # Catch any other errors
            messages.error(request, f"Error: {e}")

    return render(request, 'add_user.html')


def logout(request):
    return redirect('login')

    