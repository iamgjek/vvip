
from django.urls import re_path

from users import views



urlpatterns = [
    re_path(r'^get_company_list/$', views.GetCompanyList.as_view(), name='get_company_list'),
    re_path(r'^add_company/$', views.AddCompany.as_view(), name='add_company'),
    re_path(r'^get_company_info/$', views.GetCompanyInfo.as_view(), name='get_company_info'),
    re_path(r'^modify_company/$', views.ModifyCompany.as_view(), name='modify_company'),
]