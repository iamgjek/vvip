from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.views.generic import View, TemplateView
from django.http import HttpResponseRedirect
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from drf_spectacular.views import SpectacularSwaggerView
from drf_spectacular.settings import spectacular_settings

from rest_framework.authtoken.models import Token
from rest_framework.response import Response

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
