from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser

import uuid
# Create your models here.

class UserProfile(models.Model):
    user   = models.OneToOneField(User, on_delete=models.CASCADE)
    # avatar = models.ImageField(upload_to='avatar/%Y%m', blank=True, null=True, verbose_name='使用者頭像')
    user_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='使用者公鑰')

    class Meta:
        verbose_name = "頭像"
        verbose_name_plural = "頭像"


class User(AbstractUser):
    user   = models.OneToOneField(User, on_delete=models.CASCADE)
    # avatar = models.ImageField(upload_to='avatar/%Y%m', blank=True, null=True, verbose_name='使用者頭像')
    user_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='使用者公鑰')

    class Meta:
        verbose_name = "使用者資訊"
        verbose_name_plural = "使用者資訊"