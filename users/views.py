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

#
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    # 建立帳號時 自動觸發
    if created:
        Token.objects.create(user=instance)

# class RestfulApiView(LoginRequiredMixin, SpectacularSwaggerView):
#     TAG = '[RestfulApiView]'

#     def get(self, request, *args, **kwargs):
#         check = request.user.is_superuser
#         if check:
#             return Response(
#                 data={
#                     'title': self.title,
#                     'dist': self._swagger_ui_dist(),
#                     'favicon_href': self._swagger_ui_favicon(),
#                     'schema_url': self._get_schema_url(request),
#                     'settings': self._dump(spectacular_settings.SWAGGER_UI_SETTINGS),
#                     'oauth2_config': self._dump(spectacular_settings.SWAGGER_UI_OAUTH2_CONFIG),
#                     'template_name_js': self.template_name_js,
#                     'csrf_header_name': self._get_csrf_header_name(),
#                     'schema_auth_names': self._dump(self._get_schema_auth_names()),
#                 },
#                 template_name=self.template_name,
#             )
#         else:
#             return redirect('/')

class GetCompanyList(APIView):
    TAG = "[GetCompanyList]"

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.AllowAny]

    def process(self, request):
        result = {'status': 'NG'}
        try:
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
            state = json.loads(state)

            #* 帳號
            try:
                user = User.objects.get(username=account)
                user.first_name = contact_person
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
            company.company_name = company_name
            company.company_id = company_id
            company.sub_domain = sub_domain
            company.contact_person = contact_person
            company.phone = phone
            if upload_file:
                company.logo = upload_file
            company.open_area_list = open_area
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
            params = request.POST
            account = params.get('account', None)

            sql = f'''SELECT a.id, c.sub_domain, c.open_area_list, c.logo, a.username, a.using, c.company_name, c.company_id, c.contact_person, c.phone
                    FROM vvip.users_user a
                    left join vvip.users_companyusermapping b on b.user_id=a.id
                    left join vvip.users_company c on c.id=b.company_id
                    where a.username="{account}"'''
            datas = User.objects.raw(sql)
            for data in datas:
                data_dict = {
                            'sub_domain': data.sub_domain,
                            'open_area': json.loads(data.open_area_list) if data.open_area_list else [],
                            'logo': data.logo if data.logo else '',
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
            params = request.GET
            company_account = params.get('company_account', None)
            if not company_account:
                sql = f'''SELECT a.id, b.first_name, b.username, b.phone FROM vvip.users_companyusermapping a
                        left join vvip.users_user b on b.id=a.user_id
                        left join vvip.users_company c on c.id=a.company_id
                        where a.is_admin=0;
                        '''
            else:
                sql = f'''SELECT c.id
                        FROM vvip.users_user a
                        left join vvip.users_companyusermapping b on b.user_id=a.id
                        left join vvip.users_company c on c.id=b.company_id
                        where a.username="{company_account}"'''
                company_id = User.objects.raw(sql)[0].id
                sql = f'''SELECT a.id, b.first_name, b.username, b.phone FROM vvip.users_companyusermapping a
                        left join vvip.users_user b on b.id=a.user_id
                        left join vvip.users_company c on c.id=a.company_id
                        where a.company_id={company_id} and a.is_admin=0;
                        '''
            users = User.objects.raw(sql)
            data_list = []
            for i in users:
                data_list.append({
                    'name': i.first_name,
                    'account': i.username,
                    'phone': i.phone,
                    })

            result['status'] = 'OK'
            result['msg'] = '成功傳送資料'
            result['data'] = data_list
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
            params = request.POST
            company_account = params.get('company_account', None)
            account = params.get('account', None)
            password = params.get('password', None)
            password2 = params.get('password2', None)
            name = params.get('name', None)
            phone = params.get('phone', None)

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
            company = Company.objects.get(id=company_id, is_valid=1)

            with transaction.atomic():
                try:
                    user = User.objects.create(username=account, password=make_password(password), first_name=name, phone=phone)
                except:
                    result['msg'] = '已存在此帳號'
                    return result
                CompanyUserMapping.objects.create(user=user, company=company)

            result['status'] = 'OK'
            result['msg'] = '新增帳號成功'
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
            params = request.POST
            account = params.get('account', None)
            name = params.get('name', None)
            password = params.get('password', None)
            password2 = params.get('password2', None)
            phone = params.get('phone', None)
            delete = params.get('state', 'false')
            delete = json.loads(delete)

            #* 檢查密碼
            check_password = True if (not password2) or (password2 and password == password2) else False
            if not check_password:
                result['msg'] = '確認密碼錯誤'
                return result

            #* 帳號
            try:
                user = User.objects.get(username=account)
                user.first_name = name
                user.phone = phone
                if password:
                    user.password = make_password(password)
                if delete:
                    user.is_active = 0
            except:
                result['msg'] = '不存在的帳號'
                return result

            #* 公司
            if delete:
                cu_mapping = CompanyUserMapping.objects.filter(user=user, is_admin=0, is_valid=True)
                for i in cu_mapping:
                    i.is_valid = 0

            with transaction.atomic():
                user.save()
                #* 公司
                if delete:
                    cu_mapping = CompanyUserMapping.objects.filter(user=user, is_admin=0, is_valid=True)
                    for i in cu_mapping:
                        i.is_valid = 0

            result['status'] = 'OK'
            result['msg'] = '修改帳號資料成功'
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
            params = request.POST
            account = params.get('account', None)
            try:
                data = User.objects.get(username=account)
            except:
                result['msg'] = '不存在的帳號'
                return result
            data_dict = {
                        'account': data.username,
                        'name': data.first_name,
                        'phone': data.phone
                        }

            result['status'] = 'OK'
            result['msg'] = '取得帳號資訊成功'
            result['data'] = data_dict
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
