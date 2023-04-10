import json
import logging
import sys
import time
from datetime import date, datetime
from decimal import Decimal

import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models.fields.files import ImageFieldFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import authentication, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

from users.models import Company, CompanyUserMapping, OpenArea, User
from users.serializers import (AddCompanySerializer, GetCompanyInfoSerializer,
                               ModifyCompanySerializer, GetUserListSerializer, AddUserSerializer, ModifyUserSerializer)

logger = logging.getLogger(__name__)

def check_role(request):
    #! 檢查sub_domain
    user_id = User.objects.get(username=request.user.get_username()).id
    urls = request.build_absolute_uri('/')[:-1].strip("/")
    if '.vvips.com.tw' in urls:
        sub_domain = urls.split('.vvips.com.tw')[0].split('//')[1]
        companys = Company.objects.filter(sub_domain=sub_domain, is_valid=1)
        if companys:
            company_id = companys[0].id
        else:
            company_id = None
    else:
        company_id = 1
    #! 檢查角色
    #* role_dict = {0: 'Administrator(元宏本身)', 1: Manager(店東或廠商主管), 2: Operator(廠商旗下的業務), 3: other(非此sub_domain下的帳號)}
    #* role_dict = {0: 'Administrator(元宏本身)', 1: Admin(老闆), 2: Manager(店東或廠商主管), 3: Operator(廠商旗下的業務), 4: other(非此sub_domain下的帳號)}
    check_user = CompanyUserMapping.objects.filter(user_id=user_id, is_valid=1)
    if check_user:
        # role = 3 if company_id and check_user[0].company_id != company_id else 1 if check_user[0].is_admin == 1 else 2
        role = 4 if company_id and check_user[0].company_id != company_id else 1 if check_user[0].is_admin == 1 else 2 if check_user[0].is_manager == 1 else 3
    else:
        role = 0
    return role

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return None

class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj): # pylint: disable=E0202
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, ImageFieldFile):
            if obj:
                return obj.path
            return None
        return json.JSONEncoder.default(self, obj)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    # 建立帳號時 自動觸發
    if created:
        Token.objects.create(user=instance)

class GetCompanyList(APIView):
    TAG = "[GetCompanyList]"

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.AllowAny]

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role == 0:
                sql = '''SELECT a.id, a.company_name, c.username, a.sub_domain, a.open_area_list, a.phone, c.using FROM vvip.users_company a
                        left join vvip.users_companyusermapping b on b.company_id=a.id and b.is_admin=1
                        left join vvip.users_user c on c.id = b.user_id
                        '''
                companys = Company.objects.raw(sql)
                data_list = []
                for i in companys:
                    open_area_list = ' '.join(i.open_area_list) if i.open_area_list else ''
                    data_list.append({
                        'name': i.company_name,
                        'account': i.username,
                        'sub_domain': i.sub_domain,
                        'open_area': open_area_list,
                        'phone': i.phone,
                        'state': True if i.using else False,
                        })
                result['status'] = 'OK'
                result['msg'] = '成功傳送資料'
                result['data'] = data_list
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='取帳號列表(公司)',
        description='取帳號列表(公司)',
        request=None,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def get(self, request):
        logger.info('取帳號列表(公司)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class AddCompany(APIView):
    TAG = "[AddCompany]"

    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role == 0:
                params = request.POST
                sub_domain = params.get('sub_domain', None)
                open_area = params.get('open_area', None)
                upload_file = request.FILES.get('upload_file', None)
                account = params.get('account', None)
                password = params.get('password', None)
                password2 = params.get('password2', None)
                company_name = params.get('company_name', None)
                company_id = params.get('company_id', None)
                contact_person = params.get('contact_person', None)
                phone = params.get('phone', None)

                if not company_name:
                    result['msg'] = '公司名稱不能為空'
                    return result

                if not account:
                    result['msg'] = '帳號不能為空'
                    return result

                #* 檢查密碼
                check_password = True if (not password2) or (password2 and password == password2) else False
                if not check_password:
                    result['msg'] = '確認密碼錯誤'
                    return result

                #* 檢查公司有無重複
                company = Company.objects.filter(company_name=company_name, is_valid=1)
                if company:
                    result['msg'] = '該公司已存在'
                    return result

                #* 開放地區處理
                open_area_list = []
                city_code_dict = {}
                if open_area:
                    for k, v in json.loads(open_area).items():
                        if v:
                            city_code_dict[k] = ''
                    try:
                        url = 'https://lbor.wsos.com.tw/common/car/get_all_code/?select_type=0'
                        r = requests.get(url)
                        r = r.json()
                        for city_code in city_code_dict:
                            city_name = r[city_code]['city_name']
                            city_code_dict[city_code] = city_name
                            open_area_list.append(city_name)
                    except:
                        logger.info('取地區代碼失敗')
                        result['msg'] = '取地區代碼失敗'
                        return result

                with transaction.atomic():
                    try:
                        user = User.objects.create(username=account, password=make_password(password), first_name=contact_person, phone=phone)
                    except:
                        result['msg'] = '已存在此帳號'
                        return result
                    company = Company.objects.create(company_name=company_name, company_id=company_id, sub_domain=sub_domain, phone=phone, open_area_list=open_area_list,
                                                    contact_person=contact_person, logo=upload_file)
                    CompanyUserMapping.objects.create(user=user, company=company, is_admin=True)
                    if open_area and city_code_dict:
                        for open_area_code, open_area_str in city_code_dict.items():
                            OpenArea.objects.create(company=company, open_area_str=open_area_str, open_area_code=open_area_code)

                result['status'] = 'OK'
                result['msg'] = '新增帳號成功'
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='新增帳號(公司)',
        description='新增帳號(公司)',
        request=AddCompanySerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def post(self, request):
        logger.info('新增帳號(公司)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class ModifyCompany(APIView):
    TAG = "[ModifyCompany]"

    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role == 0:
                params = request.POST
                sub_domain = params.get('sub_domain', None)
                open_area = params.get('open_area', None)
                upload_file = request.FILES.get('upload_file', None)
                account = params.get('account', None)
                state = params.get('state', 'true')
                company_name = params.get('company_name', None)
                company_id = params.get('company_id', None)
                contact_person = params.get('contact_person', None)
                phone = params.get('phone', None)
                logo = params.get('logo', None)
                state = json.loads(state)

                #* 帳號
                try:
                    user = User.objects.get(username=account)
                    if contact_person:
                        user.first_name = contact_person
                    if phone:
                        user.phone = phone
                    user.using = state
                except:
                    result['msg'] = '不存在的帳號'
                    return result

                #* 公司
                cu_mapping = CompanyUserMapping.objects.get(user=user, is_admin=1)
                cu_mapping.is_valid = state
                cid = cu_mapping.company_id
                company = Company.objects.get(id=cid)
                if company_name:
                    company.company_name = company_name
                if company_id:
                    company.company_id = company_id
                if sub_domain:
                    company.sub_domain = sub_domain
                if contact_person:
                    company.contact_person = contact_person
                if phone:
                    company.phone = phone
                if upload_file:
                    company.logo = upload_file
                company.is_valid = state

                #* 開放地區處理
                open_area_list = []
                city_code_dict = {}
                code_list = []
                if open_area:
                    for k, v in json.loads(open_area).items():
                        if v:
                            city_code_dict[k] = ''
                            code_list.append(k)
                    try:
                        url = 'https://lbor.wsos.com.tw/common/car/get_all_code/?select_type=0'
                        r = requests.get(url)
                        r = r.json()
                        for city_code in city_code_dict:
                            city_name = r[city_code]['city_name']
                            city_code_dict[city_code] = city_name
                            open_area_list.append(city_name)
                    except:
                        logger.info('取地區代碼失敗')
                        result['msg'] = '取地區代碼失敗'
                        return result

                company.open_area_list = open_area_list

                with transaction.atomic():
                    user.save()
                    company.save()
                    cu_mapping.save()
                    if not state:
                        OpenArea.objects.filter(company=company).update(is_valid=0)
                    elif open_area and city_code_dict:
                        openarea_data = OpenArea.objects.filter(company=company, is_valid=1)
                        re_code = []
                        for i in openarea_data:
                            if not i.open_area_code in code_list:
                                i.is_valid = 0
                                i.save()
                            else:
                                re_code.append(i.open_area_code)
                        create_code_list = list(set(code_list) - set(re_code))
                        for open_area_code in create_code_list:
                            open_area_str = city_code_dict[open_area_code]
                            OpenArea.objects.create(company=company, open_area_str=open_area_str, open_area_code=open_area_code)

                result['status'] = 'OK'
                result['msg'] = '修改帳號資料成功'
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='修改帳號(公司)',
        description='修改帳號(公司)',
        request=ModifyCompanySerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def post(self, request):
        logger.info('修改帳號(公司)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class GetCompanyInfo(APIView):
    TAG = "[GetCompanyInfo]"

    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role == 0:
                params = request.POST
                account = params.get('account', None)

                city_list = {'臺北市': 'A', '基隆市': 'C', '新北市': 'F', '桃園市': 'H', '新竹市': 'O', '新竹縣': 'J', '臺中市': 'B', '苗栗縣': 'K', '彰化縣': 'N', '南投縣': 'M',
                            '雲林縣': 'P', '臺南市': 'D', '高雄市': 'E', '嘉義市': 'I', '嘉義縣': 'Q', '屏東縣': 'T', '宜蘭縣': 'G', '花蓮縣': 'U', '臺東縣': 'V'}
                sql = f'''SELECT c.id, c.sub_domain, c.open_area_list, c.logo, a.username, a.using, c.company_name, c.company_id, c.contact_person, c.phone
                        FROM vvip.users_user a
                        left join vvip.users_companyusermapping b on b.user_id=a.id
                        left join vvip.users_company c on c.id=b.company_id
                        where a.username="{account}"'''
                datas = User.objects.raw(sql)
                for data in datas:
                    c_id = data.id
                    logo = Company.objects.get(id=c_id).logo
                    city_data = json.loads(data.open_area_list) if data.open_area_list else []
                    city_dict = {city_list[i]: True for i in city_data} if city_data else {}
                    data_dict = {
                                'sub_domain': data.sub_domain,
                                'open_area': city_dict,
                                'logo': logo.url if logo else '',
                                'account': data.username,
                                'state': True if data.using else False,
                                'company_name': data.company_name,
                                'company_id': data.company_id,
                                'contact_person': data.contact_person,
                                'phone': data.phone
                                }

                result['status'] = 'OK'
                result['msg'] = '取得帳號資訊成功'
                result['data'] = data_dict
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='取得帳號資訊(公司)',
        description='取得帳號資訊(公司)',
        request=GetCompanyInfoSerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def post(self, request):
        logger.info('取得帳號資訊(公司)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class GetUserList(APIView):
    TAG = "[GetCompanyList]"

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.AllowAny]

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role in [0, 1, 2]:
                company_account = self.username
                sql = f'''SELECT c.id
                        FROM vvip.users_user a
                        left join vvip.users_companyusermapping b on b.user_id=a.id
                        left join vvip.users_company c on c.id=b.company_id
                        where a.username="{company_account}"'''
                company_id = User.objects.raw(sql)[0].id
                if company_id:
                    sql = f'''SELECT a.id, b.first_name, b.username, b.phone, a.open_area_str, a.is_admin, a.is_manager, a.is_operator
                            FROM vvip.users_companyusermapping a
                            left join vvip.users_user b on b.id=a.user_id
                            left join vvip.users_company c on c.id=a.company_id
                            where a.company_id={company_id} and a.is_admin=0 and a.is_valid=1 and b.using=1;
                            '''
                else:
                    sql = f'''SELECT a.id, b.first_name, b.username, b.phone, a.open_area_str, a.is_admin, a.is_manager, a.is_operator
                            FROM vvip.users_companyusermapping a
                            left join vvip.users_user b on b.id=a.user_id
                            left join vvip.users_company c on c.id=a.company_id
                            where a.is_admin=0 and a.is_valid=1 and b.using=1;
                            '''
                users = User.objects.raw(sql)
                data_list = []
                for i in users:
                    if company_account == i.username:
                        continue
                    data_list.append({
                        'name': i.first_name,
                        'account': i.username,
                        'phone': i.phone,
                        'open_area': i.open_area_str,
                        'role': 2 if i.is_admin else 0 if i.is_manager else 1 if i.is_operator else None
                        })

                result['status'] = 'OK'
                result['msg'] = '成功傳送資料'
                result['data'] = data_list
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='取帳號列表(使用者)',
        description='取帳號列表(使用者)',
        request=GetUserListSerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def get(self, request):
        self.username = User.objects.get(username=request.user.get_username()).username
        logger.info('取帳號列表(使用者)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class AddUser(APIView):
    TAG = "[AddCompany]"

    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role in [0, 1, 2]:
                params = request.POST
                company_account = self.username
                account = params.get('account', None)
                password = params.get('password', None)
                password2 = params.get('password2', None)
                name = params.get('name', None)
                phone = params.get('phone', None)
                open_area = params.get('open_area', None)
                role = params.get('role', None)

                if not role:
                    result['msg'] = '請選擇角色'
                    return result
                if not account:
                    result['msg'] = '帳號不能為空'
                    return result
                role = int(role)
                open_area_code = [i.split(';')[0] for i in json.loads(open_area)] if open_area else None

                #* 檢查密碼
                check_password = True if (not password2) or (password2 and password == password2) else False
                if not check_password:
                    result['msg'] = '確認密碼錯誤'
                    return result

                #* 取得公司id
                if company_account:
                    sql = f'''SELECT c.id
                            FROM vvip.users_user a
                            left join vvip.users_companyusermapping b on b.user_id=a.id
                            left join vvip.users_company c on c.id=b.company_id
                            where a.username="{company_account}"'''
                    company_id = User.objects.raw(sql)[0].id
                else:
                    company_id = 1
                try:
                    company = Company.objects.get(id=company_id, is_valid=1)
                except:
                    result['msg'] = '非公司帳號，無此操作權限'
                    return result

                with transaction.atomic():
                    try:
                        user = User.objects.create(username=account, password=make_password(password), first_name=name, phone=phone)
                    except:
                        result['msg'] = '已存在此帳號'
                        return result
                    if role == 0:
                        CompanyUserMapping.objects.create(user=user, company=company, open_area_str=open_area, open_area_code=open_area_code, is_manager=1)
                    else:
                        CompanyUserMapping.objects.create(user=user, company=company, open_area_str=open_area, open_area_code=open_area_code, is_operator=1)

                result['status'] = 'OK'
                result['msg'] = '新增帳號成功'
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='新增帳號(使用者)',
        description='新增帳號(使用者)',
        request=AddUserSerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def post(self, request):
        self.username = User.objects.get(username=request.user.get_username()).username
        logger.info('新增帳號(使用者)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class ModifyUser(APIView):
    TAG = "[ModifyCompany]"

    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, request):
        result = {'status': 'NG'}
        try:
            o_role = check_role(request)
            if o_role in [0, 1, 2, 3]:
                params = request.POST
                account = params.get('account', None)
                name = params.get('name', None)
                password = params.get('password', None)
                password2 = params.get('password2', None)
                phone = params.get('phone', None)
                delete = params.get('state', 'false')
                delete = json.loads(delete)
                open_area = params.get('open_area', None)
                role = params.get('role', None)
                open_area_code = [i.split(';')[0] for i in json.loads(open_area)] if open_area else None

                #* 檢查密碼
                check_password = True if (not password2) or (password2 and password == password2) else False
                if not check_password:
                    result['msg'] = '確認密碼錯誤'
                    return result

                #* 帳號
                check_user = False
                try:
                    user = User.objects.get(username=account)
                    #! 不能自己修改自己
                    if self.user.id == user.id:
                        check_user = True
                    if name:
                        user.first_name = name
                    if phone:
                        user.phone = phone
                    if password:
                        user.password = make_password(password)
                    if check_user and delete:
                        result['msg'] = '不能自己刪自己'
                        return result
                    elif delete:
                        user.is_active = 0
                except:
                    result['msg'] = '不存在的帳號'
                    return result

                with transaction.atomic():
                    user.save()
                    #* 公司
                    cu_mapping = CompanyUserMapping.objects.filter(user=user, is_admin=0, is_valid=True)
                    for i in cu_mapping:
                        if delete:
                            i.is_valid = 0
                        if check_user and open_area != i.open_area_str:
                            result['msg'] = '不能改自己開放地區'
                            return result
                        elif open_area:
                            i.open_area_str = open_area
                            i.open_area_code = open_area_code
                        if check_user and role != o_role:
                            result['msg'] = '不能改自己角色'
                            return result
                        if role == 0:
                            i.is_admin = 0
                            i.is_manager = 1
                            i.is_operator = 0
                        elif role == 1:
                            i.is_admin = 0
                            i.is_manager = 0
                            i.is_operator = 1
                        i.save()
                result['status'] = 'OK'
                result['msg'] = '修改帳號資料成功'
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='修改帳號(使用者)',
        description='修改帳號(使用者)',
        request=ModifyUserSerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def post(self, request):
        self.user = User.objects.get(username=request.user.get_username())
        logger.info('修改帳號(使用者)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

class GetUserInfo(APIView):
    TAG = "[GetCompanyInfo]"

    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, request):
        result = {'status': 'NG'}
        try:
            role = check_role(request)
            if role in [0, 1, 2]:
                params = request.POST
                account = params.get('account', None)
                try:
                    data = User.objects.get(username=account)
                    cu_mapping = CompanyUserMapping.objects.filter(user=data, is_admin=0, is_valid=True)[0]
                except:
                    result['msg'] = '不存在的帳號'
                    return result
                data_dict = {
                            'account': data.username,
                            'name': data.first_name,
                            'phone': data.phone,
                            'open_area': json.loads(cu_mapping.open_area_str) if cu_mapping.open_area_str else [],
                            'role': 2 if cu_mapping.is_admin else 0 if cu_mapping.is_manager else 1 if cu_mapping.is_operator else None
                            }

                result['status'] = 'OK'
                result['msg'] = '取得帳號資訊成功'
                result['data'] = data_dict
            else:
                result['msg'] = '無權限'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    @extend_schema(
        summary='取得帳號資訊(使用者)',
        description='取得帳號資訊(使用者)',
        request=GetCompanyInfoSerializer,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )

    def post(self, request):
        logger.info('取得帳號資訊(使用者)')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")
