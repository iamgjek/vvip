
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)
from rest_framework import routers

from v_search import views



urlpatterns = [
    re_path(r'^get_search_responseV3/$', views.GetSearchResponseV3View.as_view(), name='get_search_responseV3'),
    re_path(r'^get_plan_name/$', views.GetPlanNameView.as_view(), name='get_plan_name'),
]