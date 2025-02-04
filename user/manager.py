from django.contrib.auth.models import BaseUserManager
from .roles import Role

class CustomUserManager(BaseUserManager):
    def create_superuser(self, email=None, password=None, **extra_fields):
        """
        Create and return a superuser with email, password, and additional fields.
        """
        if not email:
            raise ValueError('The Email field must be set')

        # Normalize email
        email = self.normalize_email(email)
        role = Role.objects.get(name='admin')

        # Create user instance
        user = self.model(email=email, role=role, **extra_fields)

        # Set password
        user.set_password(password)

        # Set user as staff and superuser
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user
