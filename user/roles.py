from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        db_table = 'c_roles'

    def __str__(self):
        return self.name
