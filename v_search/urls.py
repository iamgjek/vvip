
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)
from rest_framework import routers

from v_search import views

urlpatterns = [
    re_path(r'^login/$', views.LoginView.as_view(), name='login'),
    re_path(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    re_path(r'^land_dev/$', views.LandDevView.as_view(), name='land_dev'),
    re_path(r'^get_search_responseV3/$', views.GetSearchResponseV3View.as_view(), name='get_search_responseV3'),
    re_path(r'^get_plan_name/$', views.GetPlanNameView.as_view(), name='get_plan_name'),
    re_path(r'^get_city/$', views.GetCityListView.as_view(), name='get_city'),
    re_path(r'^get_area/$', views.GetAreaListView.as_view(), name='get_area'),
    re_path(r'^get_region/$', views.GetRegionListView.as_view(), name='get_region'),

    re_path(r'^account_manage_login/$', views.AccountManageLoginView.as_view(), name='account_manage_login'),
    re_path(r'^account_manage/$', views.AccountManageView.as_view(), name='account_manage'),
    re_path(r'^account_edit/$', views.AccountEditView.as_view(), name='account_edit'),
    re_path(r'^account_add/$', views.AccountAddView.as_view(), name='account_add'),

    re_path(r'^member_pw/$', views.MemberPwView.as_view(), name='member_pw'),
    re_path(r'^member_aclist/$', views.MemberAclistView.as_view(), name='member_aclist'),
    re_path(r'^member_newac/$', views.MemberNewacView.as_view(), name='member_newac'),
    re_path(r'^member_editac/$', views.MemberEditacView.as_view(), name='member_editac'),
    #* 取得logo
    re_path(r'^get_logo/$', views.GetLogoView.as_view(), name='get_logo'),
    #* 總歸戶
    re_path(r'^personal_property/$', views.PersonalPropertyView.as_view(), name='personal_property'),
    #* pdf下載
    re_path(r'pdf_download/(?P<token>[0-9a-zA-Z_-]+)/$', views.TranscriptDownloadView.as_view(), name='pdf_download'),
    #* 設定地建號等級
    re_path(r'set_lbkey_rank/$', views.SetLBkeyRankView.as_view(), name='set_lbkey_rank'),
]