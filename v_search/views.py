from django.shortcuts import render
from django.views.generic.base import TemplateView, View
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

import logging

# Create your views here.
logger = logging.getLogger(__name__)

class IndexView(TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        if self.request.GET.get('next'):
            logger.debug('I see next!!!')
            context['next'] = self.request.GET.get('next')
        if self.request.GET.get('display_main'):
            logger.debug('I see display_main!!!')
            context['display_main'] = self.request.GET.get('display_main')
        debug = False
        if not self.request.user.is_anonymous:
            context['first_name'] = self.request.user.first_name if len(self.request.user.first_name) > 0 else None
            context['user_name'] = self.request.user.username
            if self.request.user.username:
                user = User.objects.get(username=self.request.user.username)
                uid = user.id
                role, role_obj, user, downstream = self.find_role(uid=uid)
                if role_obj:
                    crm_user = True
            if settings.DEBUG == True:
                debug = True
        context['debug'] = debug
        return context
