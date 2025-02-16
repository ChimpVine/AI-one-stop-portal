# user/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from .manager import CustomUserManager
from .roles import Role
from rest_framework_simplejwt.tokens import RefreshToken

class CustomUser(AbstractUser):
    email = models.EmailField(max_length=50, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='users', default=2)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager() 

    class Meta:
        db_table = "c_users"

    def __str__(self):
        return f"[{self.id}: {self.email}]"

    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }