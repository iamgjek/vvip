import json
import os
from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractUser, User
from django.db import models
# from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


class CustomJSONField(models.JSONField):
    ''' json 的 Field'''
    def get_prep_value(self, value):
        if value is None:
            return value
        return json.dumps(value, ensure_ascii=False)

class MediaStorage(S3Boto3Storage):
    location = settings.AWS_MEDIA_LOCATION
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False

# class LocalMediaStorage(FileSystemStorage):
#     pass

def path_and_rename(instance, filename):
    upload_to = '{}/{:02d}/{:02d}/'.format(datetime.now().year,datetime.now().month,datetime.now().day)
    ext = filename.split('.')[-1]
    filename = '{}.{}'.format(uuid4().hex, ext)
    return os.path.join(upload_to, filename)

def get_storage():
    file_storage = MediaStorage()
    return file_storage

class User(AbstractUser):
    using = models.BooleanField(default=True, verbose_name='是否啟用')
    user_token = models.UUIDField(default=uuid4, unique=True, verbose_name='使用者公鑰')

    class Meta:
        verbose_name = "使用者資訊"
        verbose_name_plural = "使用者資訊"
        indexes = [
            models.Index(fields=['using']),
        ]

    def __str__(self):
        return '{}'.format(self.username)

class Company(models.Model):
    company_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='公司名稱')
    company_id = models.CharField(max_length=10, null=True, blank=True, verbose_name='統編')
    sub_domain = models.CharField(max_length=100, null=True, blank=True, verbose_name='子域')
    contact_person = models.CharField(max_length=100, null=True, blank=True, verbose_name='聯絡人')
    phone = models.CharField(max_length=30, null=True, blank=True, verbose_name='電話')
    logo = models.ImageField(null=True, blank=True, upload_to=path_and_rename, storage=get_storage(), verbose_name='上傳logo')
    is_valid = models.BooleanField(default=True, verbose_name='是否有效')
    create_time = models.DateTimeField(auto_now_add=True, null=False, blank=False, verbose_name='建立時間')
    update_time = models.DateTimeField(null=True, blank=True, verbose_name='最後更新時間')

    class Meta:
        verbose_name = "公司資訊"
        verbose_name_plural = "公司資訊"
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['user']),
            models.Index(fields=['is_valid']),
        ]

class OpenArea(models.Model):
    company = models.ForeignKey(Company, blank=True, null=True, on_delete=models.CASCADE, verbose_name='公司')
    open_area_str = models.CharField(max_length=100, null=True, blank=True, verbose_name='開放地區')
    open_city_code = models.CharField(max_length=1, null=True, blank=True, verbose_name='開放地區(縣市代碼)')
    open_area_code = models.CharField(max_length=2, null=True, blank=True, verbose_name='開放地區(行政區代碼)')
    is_valid = models.BooleanField(default=True, verbose_name='是否有效')
    create_time = models.DateTimeField(auto_now_add=True, null=False, blank=False, verbose_name='建立時間')
    update_time = models.DateTimeField(null=True, blank=True, verbose_name='最後更新時間')

    class Meta:
        verbose_name = "開放地區清單"
        verbose_name_plural = "開放地區清單"
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['open_city_code']),
            models.Index(fields=['open_area_code']),
            models.Index(fields=['is_valid']),
        ]

class CompanyUserMapping(models.Model):
    company = models.ForeignKey(Company, blank=True, null=True, on_delete=models.CASCADE, verbose_name='公司')
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE, verbose_name='使用者')
    is_valid = models.BooleanField(default=True, verbose_name='是否有效')
    create_time = models.DateTimeField(auto_now_add=True, null=False, blank=False, verbose_name='建立時間')
    update_time = models.DateTimeField(null=True, blank=True, verbose_name='最後更新時間')

    class Meta:
        verbose_name = "公司和使用者對照表"
        verbose_name_plural = "公司和使用者對照表"
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['user']),
            models.Index(fields=['is_valid']),
        ]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # avatar = models.ImageField(upload_to='avatar/%Y%m', blank=True, null=True, verbose_name='使用者頭像')
    user_token = models.UUIDField(default=uuid4, unique=True, verbose_name='使用者公鑰')

    class Meta:
        verbose_name = "頭像"
        verbose_name_plural = "頭像"
