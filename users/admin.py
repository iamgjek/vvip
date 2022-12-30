from django.contrib import admin
from users import models

# from users.models import UserProfile
# from django.contrib.auth.models import User
# from django.contrib.auth.admin import UserAdmin as AuthUserAdmin


class UserAdmin(admin.ModelAdmin):
    list_display=('username', 'last_login', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    fields = ['username', 'password', 'last_login', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'sub_domain']
    search_fields = ['username']
    readonly_fields = ['username']

admin.site.register(models.User, UserAdmin)

# class UserProfileInline(admin.StackedInline):
#     model = UserProfile
#     max_num = 1
#     can_delete = False

# class UserAdmin(AuthUserAdmin):
#     inlines = [UserProfileInline]

# # 註銷舊用戶管理員
# admin.site.unregister(User)
# # 註冊新用戶管理員
# admin.site.register(User, UserAdmin)

# @admin.register(UserProfile)
# class Share_receiptAdmin(admin.ModelAdmin):
#     list_display = ('user',)
