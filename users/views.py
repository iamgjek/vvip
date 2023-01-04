import json
import sys
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.fields.files import ImageFieldFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import HttpResponseRedirect, redirect, render
from django.views.generic import TemplateView, View
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from users.models import Company, CompanyUserMapping, OpenArea, User


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

class GetCompanyList(LoginRequiredMixin, View):
    TAG = "[GetCompanyList]"

    def process(self, request):
        result = {'status': 'NG'}
        try:
            sql = ''''''
            companys = Company.objects.raw()
            data_list = []
            for i in companys:
                data_list.append({
                    'name': i.name,
                    'address': i.address,
                    'city': i.city,
                   'state': i.state,})

            result['status'] = 'OK'
            result['msg'] = '成功傳送資料'
        except Exception as e:
            print(e, 'exception in line', sys.exc_info()[2].tb_lineno)
            result['msg'] = '發生不可預期的錯誤，請聯繫官方客服'
        return result

    def get(self, request):
        result = self.process(request)
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")
