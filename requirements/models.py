from django.db import models

class UsersSupport(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ('editor', 'Editor User'),
            ('reviewer', 'Reviewer User'),
            ('internal', 'Internal User'),
        )