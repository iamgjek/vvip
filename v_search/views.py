import json
import logging
import time
import operator

from functools import reduce
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import requests
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         JsonResponse)
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.utils import timezone
from django.views.generic.base import TemplateView, View
from drf_spectacular.utils import (OpenApiCallback, OpenApiExample,
                                   OpenApiParameter, OpenApiResponse,
                                   Serializer, extend_schema,
                                   inline_serializer)
from rest_framework import authentication, generics, permissions, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from t_search.models import info_config
from v_search.serializers import GetSearchSerializer, PlanNameSerializer
from v_search.util import CustomJsonEncoder, get_dba

logger = logging.getLogger(__name__)
DB_NAME = 'diablo'
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return None

class NormalTemplateView(TemplateView):
    TAG = '[NormalTemplateView]'

    def get_context_data(self, **kwargs):
        context = super(NormalTemplateView, self).get_context_data(**kwargs)
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
            if settings.DEBUG == True:
                debug = True
            user_token = Token.objects.get(user=self.request.user).key
            context = {"user_token": user_token}
        context['debug'] = debug
        return context

class IndexView(NormalTemplateView):
    TAG = '[IndexView]'
    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if not self.request.user.is_anonymous:
            return redirect('/v_search/land_dev/')
        return render(request, self.template_name, context=context)

class LandDevView(NormalTemplateView):
    TAG = '[LandDevView]'
    template_name = 'land_dev.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class AccountManageLoginView(NormalTemplateView):
    TAG = '[AccountManageLoginView]'
    template_name = 'account_manage_login.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if not self.request.user.is_anonymous:
            return redirect('/v_search/account_manage/')
        return render(request, self.template_name, context=context)

class AccountManageView(NormalTemplateView):
    TAG = '[AccountManageView]'
    template_name = 'account_manage.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class AccountEditView(NormalTemplateView):
    TAG = '[AccountEditView]'
    template_name = 'account_edit.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class AccountAddView(NormalTemplateView):
    TAG = '[AccountAddView]'
    template_name = 'account_add.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class MemberPwView(NormalTemplateView):
    TAG = '[MemberPwView]'
    template_name = 'member_pw.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class MemberAclistView(NormalTemplateView):
    TAG = '[MemberAclistView]'
    template_name = 'member_aclist.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class MemberNewacView(NormalTemplateView):
    TAG = '[MemberNewacView]'
    template_name = 'member_newac.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class MemberEditacView(NormalTemplateView):
    TAG = '[MemberEditacView]'
    template_name = 'member_editac.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        if self.request.user.is_anonymous:
            return redirect('/')
        return render(request, self.template_name, context=context)

class LoginView(View):
    # authentication_classes = (CsrfExemptSessionAuthentication, )
    def post(self, request):
        result = {"status": "NG", "msg": 'not login'}
        try:
            account = request.POST.get('login')
            passwd = request.POST.get('password')
            remember = request.POST.get('remember')
            user = authenticate(username=account, password=passwd)
            if user is not None:
                login(request, user)
                if remember !='true':
                    request.session.set_expiry(0)
                    request.session.modified = True
                result = {"status": "OK", "msg": 'login'}
                logger.debug(result)
                return HttpResponse(json.dumps(result, ensure_ascii=False), content_type="application/json; charset=utf-8")
        except Exception as error:
            result['error'] = "{}".format(error)
            logger.debug(result)
        return HttpResponseBadRequest(json.dumps(result, ensure_ascii=False), content_type="application/json; charset=utf-8")

class LogoutView(View):

    def get(self, request):
        logout(request)
        result = {'status': 'OK', 'msg': 'logout'}
        return HttpResponse(json.dumps(result, ensure_ascii=False), content_type="application/json; charset=utf-8")

class GetCityListView(APIView):
    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='取縣市',
        description='取縣市',
        request=None,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )
    def get(self, request):
        res = {}
        url = f'{settings.LBOR_V3_HOST}/common/car/get_city/'
        result = requests.get(url)
        res = json.loads(result.text)
        return Response(res)

class GetAreaListView(APIView):
    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.AllowAny]
    @extend_schema(
        summary='取行政區',
        description='取行政區',
        request=None,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )
    def get(self, request):
        res = {}
        city_code = request.GET.get('city')
        url = f'{settings.LBOR_V3_HOST}/common/car/get_area/?city={city_code}'
        result = requests.get(url)
        res = json.loads(result.text)
        return Response(res)

class GetRegionListView(APIView):
    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='取段小段',
        description='取段小段',
        request=None,
        responses={
            200: OpenApiResponse(description='ok'),
            401: OpenApiResponse(description='身分認證失敗'),
        },
    )
    def get(self, request):
        res = {}
        city_code = request.GET.get('city')
        area_code = request.GET.get('area')
        url = f'{settings.LBOR_V3_HOST}/common/car/get_region/?area={area_code}&city={city_code}'
        result = requests.get(url)
        res = json.loads(result.text)
        return Response(res)

class GetPlanNameView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def process(self, datas):
        name_res, nickname_res = [], []
        area = datas.get('area')
        sql = f"SELECT T1.lbkey, T2.plan_name, T2.nickname \
                FROM diablo.t_search_landdevelopementlkeyslist T1 LEFT JOIN diablo.t_search_landdevelopementlist T2 on T1.plan_id = T2.plan_id \
                WHERE T2.valid =1 and lbkey LIKE '{area}%' \
                "
        res, col = get_dba(sql_cmd=sql, db_name=DB_NAME)
        data_df = pd.DataFrame(res)
        if data_df.empty:
            pass
        else:
            group_name = data_df['plan_name'].to_list()
            name_res = list(set(group_name))
            group_nickname = data_df['nickname'].to_list()
            nickname_res = list(set(group_nickname))

        sql_lmlandlist = f"SELECT plan_name FROM diablo.t_search_lmlandlist WHERE lkey LIKE '{area}%' and plan_name !='' group by plan_name"
        res_lm, col_lm = get_dba(sql_cmd=sql_lmlandlist, db_name=DB_NAME)
        data_df_lm = pd.DataFrame(res_lm)
        pn_df = data_df_lm['plan_name'].to_list()
        pn_list = list(set(pn_df))
        pn_list = sorted(pn_list)
        nickname_res = sorted(nickname_res)
        # print(pn_list)
        # print(nickname_res)
        return pn_list, nickname_res # name_res
    
    @extend_schema(
        summary='取 縣市/行政區/計劃案名',
        description='''
                    縣市:   https://lbor.wsos.com.tw/common/car/get_city/
                    行政區: https://lbor.wsos.com.tw/common/car/get_area/?city=A
                    段小段: https://lbor.wsos.com.tw/common/car/get_region/?area=01&city=A
                    ''',
        request=PlanNameSerializer,
        responses={
            200: OpenApiResponse(description='處理成功'),
            401: OpenApiResponse(description='身分認證失敗'),
            },
        )
    def post(self, request):
        result = {}
        serializer = PlanNameSerializer(data=request.data)
        
        if not serializer.is_valid():
            raise ParseError('格式錯誤')
        else:
            name_res, nickname_res = self.process(request.data)
            result['plan_name'] = name_res
            result['nick_name'] = nickname_res
        return Response(result)

class GetSearchResponseV3View(APIView):
    authentication_classes = [authentication.TokenAuthentication, authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    ownership_out = {
        1: "自然人", 
        2: "私法人", 
        3: "公法人", 
        4: "非公有",
        5: "部份公有",
        0: "不詳"
        }

    ownership_dict = {
        "natural": 1, 
        "private": 2, 
        "public": 3, 
        "non_public": 4,
        "partially_public": 5,
        "all": 0
        }

    main_purpose_dict = {
        "dwelling": '1',
        "store": '2',
        "office": '3',
        "factory": '4',
        "business": '5',
        "land": '6',
        "farm": '7',
        "storage": '8',
        "national": '9',
        "market": '10',
        "parking": '11',
        "other": '12'
        }

    uid_tag_out = {
        0: "未知",
        1: "本國人",
        2: "外國人",
        3: "港澳中國居民",
        }
    
    def check_int(self, num):        
        if isinstance(num, (int, float)) == True:
            return num
        elif isinstance(num, str) == True:
            try:
                num = eval(num)
            except:
                num = 0
            return num
        else:
            return num

    def to_AllList(self, result):
        base_list = []
        dic = {}
        for i in result:
            bd = {}
            bd[i[0]] = i[1]
            base_list.append(bd)
        for _ in base_list:
            for k,v in _.items():
                dic.setdefault(k,[]).append(v)
        return dic

    def do_output_dict(self, qs):
        if qs:
            tup_list = []
            for i in qs:
                data = (i.lbkey, i.regno)
                tup_list.append(data)
            result = self.to_AllList(tup_list)
            return result

    def re_regionV2(self, data):
        result_list = []
        star_list = []
        if data:
            data = data.replace(' ', '')
            region_list = data.split(',')
            if region_list:
                for region in region_list:
                    if region.find('*') != -1:
                        if region.find('-') != -1:
                            rl_star = region.split('-')[0].rjust(4, '0')
                            s1 = f'{rl_star}-0000'
                            s2 = f'{rl_star}-9999'
                            stt = (s1, s2)
                            star_list.append(stt)

                    elif region.find('*') == -1:
                        if region.find('-') != -1:
                            re_reg = region.split('-')
                            a01 = re_reg[0].rjust(4, '0')
                            a02 = re_reg[1].rjust(4, '0')
                            r_str = f'{a01}-{a02}'
                            result_list.append(r_str)
                        else:
                            b01 = region.rjust(4, '0')
                            br_str = f'{b01}-0000'
                            result_list.append(br_str)
        return result_list, star_list

    def yearsagoV2(self, years, from_date=None):
        if years:

            if from_date is None:
                from_date = datetime.now()
            try:
                from_date = from_date.replace(year=from_date.year - years)
                from_date_str = from_date.strftime("%Y-%m-%d")
                return from_date_str
            except ValueError:
                # Must be 2/29!
                assert from_date.month == 2 and from_date.day == 29 # can be removed
                from_date = from_date.replace(month=2, day=28, year=from_date.year-years)
                from_date_str = from_date.strftime("%Y-%m-%d")
                # print(from_date_str)
                return from_date_str
        else:
            return None

    def use_zone_re(self, use_zone_str):
        new_str = use_zone_str
        need_str = ['其他使用', '甲種', '乙種', '丙種', '丁種', '古蹟', '生態', '保安', '特定事業', '特定目的', '體育', '運動']
        if use_zone_str:
            new_str = use_zone_str.replace('用地', '').replace('區', '')
            for need in need_str:
                if need in new_str:
                    new_str = need
        return new_str

    def apply_uid_tag(self, uid_tag):
        data = self.uid_tag_out.get(uid_tag)
        return data

    def apply_owner_type(self, owner_type):
        data = self.ownership_out.get(owner_type)
        return data

    def apply_owners_num(self, df_data, lbkey_dict):
        get_owner_num = lbkey_dict.get(df_data['lbkey'], 0)

        return get_owner_num

    def apply_creditors_rights(self, creditors_rights):
        data = []        
        if creditors_rights in ['None', 'none', None, np.NaN, []]:
            return data

        if creditors_rights:
            data = creditors_rights.replace('\'', '\"')
            data = json.loads(data)
        return data

    def sql_str_combin(self, condition_list):
        # base sql
                    # {col}
        sql_str =  "\
                    SELECT {col} \
                    FROM \
                    diablo.{tr1} T1 \
                    left join diablo.{t2} T2 on T1.lbkey =  T2.{lbk} \
                    WHERE {where_sql} LIMIT 100000 \
        #             "
        #             # 500000
        # sql_str =  "\
        #             SELECT {col} \
        #             FROM \
        #             diablo.{tr1} T1 \
        #             left join (select city_name,area_name,region_name,lno,national_land_zone,plan_name,land_zone,urban_name,land_area,land_notice_value,build_num,owner_type,urban_type ,owners_num, land_zone_code,lkey from diablo.{t2} T2 WHERE {where_sql} LIMIT 3000) T2 on T1.lbkey =  T2.{lbk} \
        #             WHERE {where_sql} and T1.remove_time is null"
        
        condition = ''
        if condition_list:
            for ind, i in enumerate(condition_list):
                if ind == 0:
                    i = i.replace('and', '')
                condition += f' {i}'


        # 欄位後面要空格 換行要加斜線
        if self.json_lbtype == 'land':
            # select_colunm = "\
            #                 T1.id, T1.regno, T1.remove_time, T1.property_type, \
            #                 T2.plan_name, T2.land_zone, T2.urban_name, 2.land_notice_value, \
            #                 T2.build_num, T2.land_area, T2.other_remark, T2.national_land_zone, \
            #                 T1.reg_reason_str, T1.reg_date_str, T1.name, T1.uid, T1.address_re, T1.right_str, T1.shared_size, \
            #                 T1.creditors_rights, T1.is_valid \
            #                 "
            # 土地新欄位vvip用
            select_colunm = "\
                            T2.city_name, T2.area_name, T2.region_name, T2.lno, \
                            T2.national_land_zone, T2.plan_name, T2.land_zone, T2.urban_name, T2.land_area, T2.land_notice_value, \
                            T2.build_num, T2.owner_type, T2.urban_type ,T2.owners_num, T2.land_zone_code, \
                            T1.lbkey, T1.regno, T1.reg_date_str, T1.reg_reason_str, T1.name, \
                            T1.uid, T1.uid_tag, T1.address_re, T1.bday, T1.right_str, T1.shared_size, T1.creditors_rights, \
                            T1.is_valid, T1.remove_time, \
                            T1.reg_reason, T1.right_type, T1.case_type, T1.restricted_type \
                            "

        sql = sql_str.format(
                            col=select_colunm,
                            tr1 = self.t_s_regno_tbname,
                            t2 = self.t_s_mark_tbname,
                            lbk = self.col_set_lbkey,
                            where_sql = condition,
                            limit = self.data_limit)
        # print(sql)
        return sql

    def set_sql_db(self, lbtype, sb='sr'):
        if lbtype == 'L':
            if sb == 'pack':
                t_s_pack_tbname = 't_search_packs'
                t_s_regno_pack_tbname = 't_search_packlkeysregnos'
                t_s_pack_tbname = 't_search_packlkeys'
            else:
                t_s_pack_tbname = ''
                t_s_regno_pack_tbname = ''

            t_s_mark_tbname = 't_search_lmlandlist'
            t_s_regno_tbname = 't_search_lkeyregnolist'
            t_s_sc_tbname = 't_search_subscribelkeys'
            t_s_sc_reg_tbname = 't_search_subscribelkeysregnos'
            col_set_lbkey = 'lkey'            
        else:
            if sb == 'pack':
                t_s_pack_tbname = 't_search_packs'
                t_s_regno_pack_tbname = 't_search_packbkeysregnos'
                t_s_pack_tbname = 't_search_packbkeys'
            else:
                t_s_pack_tbname = ''
                t_s_regno_pack_tbname = ''

            t_s_mark_tbname = 't_search_bmbuildlist'
            t_s_regno_tbname = 't_search_bkeyregnolist'
            t_s_sc_tbname = 't_search_subscribebkeys'
            t_s_sc_reg_tbname = 't_search_subscribebkeysregnos'
            col_set_lbkey = 'bkey'

        return (t_s_mark_tbname, t_s_regno_tbname, 
                t_s_sc_tbname, t_s_sc_reg_tbname, 
                col_set_lbkey, 
                t_s_pack_tbname, t_s_regno_pack_tbname)

    def format_data_layout_fake_data(self, data):
        result = {}
        if data:
            df = pd.DataFrame(data)
            try:
                df_group = df.groupby(['region_name', 'lno'])
                for gp_index in list(df_group.size().index):
                    dict_key = f'{gp_index[0]}_{gp_index[1]}'
                    group_data = df_group.get_group(gp_index).to_dict('records')
                    result[dict_key] = group_data
            except Exception as e:
                print(e)
        return result

    def format_data_layout(self, data):
        result_land = {}
        result_owner = {}
        result = {'land_data': {}, 'owner_data': {}}
        if data.empty:
            return result
        else:            
            # 刪除多餘欄位
            for col in self.df_delete_column_list:
                try:
                    data = data.drop(col, axis=1)
                except:
                    pass

            data['owner_type'] = data['owner_type'].apply(self.apply_owner_type)
            data['uid_tag']  = data['uid_tag'].apply(self.apply_uid_tag)
            data['creditors_rights'] = data['creditors_rights'].apply(self.apply_creditors_rights)
            # group
            try:
                df_group_land = data.groupby(['region_name', 'lno'])
                for gp_index in list(df_group_land.size().index):
                    dict_key = f'{gp_index[0]}_{gp_index[1]}'
                    group_data = df_group_land.get_group(gp_index).to_dict('records')
                    result_land[dict_key] = group_data
                    result['land_data'] = result_land

            except Exception as e:
                print(f'輸出錯誤 {e}')
            try:
                df_group_owner = data.groupby(['name', 'uid', 'address_re'])
                for gp_index in list(df_group_owner.size().index):
                    dict_key = f'{gp_index[0]}_{gp_index[1]}_{gp_index[2]}'
                    group_owner_data = df_group_owner.get_group(gp_index).to_dict('records')
                    result_owner[dict_key] = group_owner_data
                    result['owner_data'] = result_owner
            except Exception as e:
                print(f'輸出錯誤 {e}')
        return result

    def clean_region_data(self, base_region):
        if base_region:
            # 計畫區
            plan = base_region.get('plan', None)
            # print(self.total_df.loc[:, ['lbkey', 'plan_name', 'owner_type']])
            if plan:
                # self.total_df = self.total_df[self.total_df['plan_name']==plan]
                self.total_df = self.total_df[self.total_df['plan_name'].str.startswith(plan)] 

            # 是否取用失效資料 打勾=1(不下條件) 目前看起來沒有這個條件
            # is_valid = base_region.get('includeInvalid', None)
            # print(is_valid)
            # if is_valid == 1:
            #     pass
            # else:                
            #     # land_qs_list.append('and T1.remove_time is null')
            #     self.total_df = self.total_df[self.total_df['remove_time']==np.nan]

            #!!!!! TODO 多筆單筆要調整!!!!!
            # 地號子母號
            dataType = -1
            land_number = base_region.get('land_number', None)
            if land_number:
                if land_number.find(',') != -1:
                    dataType = 1
                elif land_number.find('~') != -1:
                    dataType = 2
                elif len(land_number) > 1:
                    dataType = 0
                print(f'{land_number}, 型態:{dataType}')

                # 單筆
                if dataType == 0:
                    d_single = land_number # base_region.get('landNumberSingle', None)
                    fsl = []
                    result_list, star_list = self.re_regionV2(d_single)
                    if result_list:
                        if len(result_list) > 0:
                            print(result_list)
                            self.total_df = self.total_df[self.total_df['lno']==result_list[0]]

                # 多筆
                elif dataType == 1:
                    # print('多筆')
                    d_Multiple = land_number # base_region.get('landNumberMultiple', None)
                    result_list, star_list = self.re_regionV2(d_Multiple)
                    if result_list:
                        if len(result_list) > 0:
                            self.total_df = self.total_df[self.total_df['lno'].str.startswith(tuple(result_list))]

                # 區間
                elif dataType == 2:
                    try:
                        low_n = land_number.split('~')[0]
                        up_n = land_number.split('~')[1]
                        low, _ = self.re_regionV2(low_n)
                        up, _ = self.re_regionV2(up_n)
                        if len(low) and len(up):   
                            low_str = low[0]
                            up_str = up[0]
                            self.total_df = self.total_df[self.total_df['lno'].between(low_str, up_str)]

                    except Exception as e:
                        print(e)
                        pass

            # 國土分區 多筆
            n_land_zone = base_region.get('national_land_zone', None)

    def clean_condition_data(self, base_condition):
        if base_condition:
            # 登記原因 (改多筆)
            registerReason = base_condition.get('registerReason')
            if isinstance(registerReason, dict) == True:
                reg_list = []
                for x, v in registerReason.items():
                    x = int(x)
                    v = int(v)
                    # x_real = x + 1
                    if v:
                        reg_list.append(x)
                if reg_list:
                    self.total_df = self.total_df[self.total_df['reg_reason'].isin(reg_list)]

            # 權屬樣態
            ownership = base_condition.get('ownership')
            if ownership:
                oqs = [x for x, y in ownership.items() if y != 0]
                os_list = []
                for i in oqs:
                    j = self.ownership_dict.get(i)
                    if j:
                        os_list.append(j)
                if os_list:
                    # owner_type
                    pass
                    self.total_df = self.total_df[self.total_df['owner_type'].isin(os_list)]

            # 權利範圍型態 (公同共有)
            ownershipType = self.check_int(base_condition.get('ownershipType'))
            if ownershipType:
                if ownershipType == 0:
                    pass
                elif ownershipType == 1:
                    self.total_df = self.total_df[self.total_df['right_type'].isin([0, 1, 2])]
                elif ownershipType == 2:
                    self.total_df = self.total_df[self.total_df['right_type']==3]

            # 所有權人數
            o_num_low = self.check_int(base_condition.get('ownershipNumLowerLimit'))
            o_num_up = self.check_int(base_condition.get('ownershipNumUpperLimit'))
            if o_num_low == 0 and o_num_up == 0:
                pass
            else:
                if isinstance(o_num_up, int) == True and isinstance(o_num_low, int) == True:
                    self.total_df = self.total_df[(self.total_df['owner_num_real']<=o_num_up) & (self.total_df['owner_num_real']>=o_num_low)]

                elif isinstance(o_num_low, int) == True:
                    self.total_df = self.total_df[self.total_df['owner_num_real']>=o_num_low]
                elif isinstance(o_num_up, int) == True:
                    self.total_df = self.total_df[self.total_df['owner_num_real']<=o_num_up]

            # 面積分類 總 持分 平均持分 ==========================
            areaType = self.check_int(base_condition.get('areaType'))
            l_lower = self.check_int(base_condition.get('landAreaLowerLimit', None))
            l_upper = self.check_int(base_condition.get('landAreaUpperLimit', None))
            # 輸入為坪數 需轉為平方公尺
            if isinstance(l_lower, (int, float)):
                l_lower = l_lower / 0.3025
                l_lower = round(l_lower, 4)
            if isinstance(l_upper, (int, float)):
                l_upper = l_upper / 0.3025
                l_upper = round(l_upper, 4)

            # print(f'輸入區間 {l_lower}, {l_upper}  型態: {areaType}')
            if areaType != 0:
                self.total_df = self.total_df[self.total_df['right_type']==areaType]

            try:
                if l_lower == 0 and l_upper == 0:
                    pass
                else:
                    # ! 0=總面積
                    if areaType == 0:
                        if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                            if l_lower == 0 and l_upper == 0:
                                pass
                            else:
                                pass
                                # self.total_df = self.total_df[(self.total_df['land_area']<=l_upper) & (self.total_df['land_area']>=l_lower)]
                                land_area_con = (self.total_df['land_area']<=l_upper) & (self.total_df['land_area']>=l_lower)
                                share_area_con = (self.total_df['shared_size']<=l_upper) & (self.total_df['shared_size']>=l_lower)
                                self.total_df = self.total_df[(land_area_con | share_area_con)]
                        
                    elif areaType == 1:
                        if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                            if l_lower == 0 and l_upper == 0:
                                pass
                            else:
                                self.total_df = self.total_df[(self.total_df['land_area']<=l_upper) & (self.total_df['land_area']>=l_lower)]

                        elif isinstance(l_lower, (int, float)) == True:
                            self.total_df = self.total_df[self.total_df['land_area']>=l_lower]
                        elif isinstance(l_upper, (int, float)) == True:
                            self.total_df = self.total_df[self.total_df['land_area']<=l_upper]

                    # ! 1=持分面積
                    elif areaType == 2:
                        if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                            if l_lower == 0 and l_upper == 0:
                                pass
                            else:
                                self.total_df = self.total_df[(self.total_df['shared_size']<=l_upper) & (self.total_df['shared_size']>=l_lower)]

                        elif isinstance(l_lower, (int, float)) == True:
                            self.total_df = self.total_df[self.total_df['shared_size']>=l_lower]
                        elif isinstance(l_upper, (int, float)) == True:
                            self.total_df = self.total_df[self.total_df['shared_size']<=l_upper]
                        # print(self.total_df.loc[:, ['lbkey', 'land_area', 'shared_size', 'right_type', 'owner_type']])

                    # ! 1=公同共有面積
                    elif areaType == 3:
                        try:
                            self.total_df['common_part'] = self.total_df['land_area'] / self.total_df['owners_num']
                            if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                                if l_lower == 0 and l_upper == 0:
                                    pass
                                else:
                                    self.total_df = self.total_df[(self.total_df['common_part']<=l_upper) & (self.total_df['common_part']>=l_lower)]
                            elif isinstance(l_lower, (int, float)) == True:
                                self.total_df = self.total_df[self.total_df['common_part']>=l_lower]
                            elif isinstance(l_upper, (int, float)) == True:
                                self.total_df = self.total_df[self.total_df['common_part']<=l_upper]
                            self.total_df['common_part'] = pd.to_numeric(self.total_df['common_part'], errors='coerce').round(2)

                            self.total_df['shared_size'] = self.total_df['common_part']
                            # print(self.total_df.loc[:, ['lbkey', 'land_area', 'shared_size', 'right_type', 'owner_type','common_part']])
                            self.total_df = self.total_df.drop('common_part', axis=1)
                        except Exception as e:
                            print(f'公同共有面積錯誤 ：{e}')
            except Exception as e:
                print(f'面積錯誤 ：{e}')

            # 去小數
            self.total_df['land_area'] = pd.to_numeric(self.total_df['land_area'], errors='coerce').round(2)
            self.total_df['shared_size'] = pd.to_numeric(self.total_df['shared_size'], errors='coerce').round(2)

            # 使用區分類
            in_city = [self.use_zone_re(x) for x, v in base_condition.get('inCity', {}).items() if v]
            out_city = [self.use_zone_re(x) for x, v in base_condition.get('outCity', {}).items() if v]
            outCity2 = [self.use_zone_re(x) for x, v in base_condition.get('outCity2', {}).items() if v]
            road_land = base_condition.get('road_land', None)
            common_land = base_condition.get('common_land', None)
            # print(road_land, common_land)
            # print(self.total_df.loc[:, ['lbkey', 'urban_name', 'land_zone', 'right_type', 'owner_type']])
            total_con = []
            # self.total_df['urban_name'] = self.total_df['urban_name'].fillna('')
            # self.total_df['land_zone'] = self.total_df['land_zone'].fillna('')
            # self.total_df['land_zone_code'] = self.total_df['land_zone_code'].fillna('')

            if in_city or out_city:
                # 搜尋2個欄位
                con1 = self.total_df['urban_name'].str.contains('|'.join(in_city+out_city), na=False)
                total_con.append(con1)
                con2 = self.total_df['land_zone'].str.contains('|'.join(in_city+out_city), na=False)   
                total_con.append(con2)

            if outCity2:
                con3 = self.total_df['urban_name'].str.startswith(tuple(outCity2), na=False)
                total_con.append(con3)
            if road_land:
                con4 = self.total_df['land_zone_code']=='C11'
                total_con.append(con4)
            if common_land:
                con5 = self.total_df['land_zone_code'].str.startswith('C', na=False)
                total_con.append(con5)

            if total_con:
                self.total_df = self.total_df[reduce(operator.or_, total_con)]

            # 公告現值
            vp_lower = self.check_int(base_condition.get('presentLowerLimit', None))
            vp_upper = self.check_int(base_condition.get('presentUpperLimit', None))
            vp_lower = vp_lower * 10000
            vp_upper = vp_upper * 10000
            self.total_df['land_notice_value'] = pd.to_numeric(self.total_df['land_notice_value'], errors='coerce')
            if vp_lower == 0 and vp_upper == 0:
                pass
            else:
                if isinstance(vp_lower, int) == True and isinstance(vp_upper, int) == True:
                    self.total_df = self.total_df[(self.total_df['land_notice_value']<=vp_upper) & (self.total_df['land_notice_value']>=vp_lower)]
                elif isinstance(vp_lower, int) == True:
                    self.total_df = self.total_df[self.total_df['land_notice_value']>=vp_lower]
                elif isinstance(vp_upper, int) == True:
                    self.total_df = self.total_df[self.total_df['land_notice_value']<=vp_upper]

            # 總公告
            self.total_df['total_vp'] = self.total_df['land_area'] * self.total_df['land_notice_value']


    def clean_other_data(self, base_other):

        # 他項設定:他項標記
        cast_type = self.check_int(base_other.get('otherRemark', None))
        if cast_type in [None, 'None', 'null']:
            pass
        else:
            self.total_df = self.total_df[self.total_df['case_type']==cast_type]

        # 他項設定:限制登記
        restricted_type = self.check_int(base_other.get('restrictedRegistration', None))
        if restricted_type in [None, 'None', 'null']:
            pass
        else:
            self.total_df = self.total_df[self.total_df['restricted_type']==restricted_type]

        # 年齡範圍
        age_range = self.check_int(base_other.get('age_range', None))

        # 國籍
        country = self.check_int(base_other.get('country', None))
        
        # 個人持分總值 ｜ 持分現值
        pv_lower = self.check_int(base_other.get('p_part_valueLowerLimit', None))
        pv_upper = self.check_int(base_other.get('p_part_valueUpperLimit', None))
        pv_lower = pv_lower * 10000
        pv_upper = pv_upper * 10000

        self.total_df['present_value'] = self.total_df['shared_size'] * self.total_df['land_notice_value']
        if pv_lower == 0 and pv_upper == 0:
            pass
        else:
            if isinstance(pv_lower, int) == True and isinstance(pv_upper, int) == True:
                self.total_df = self.total_df[(self.total_df['present_value']<=pv_upper) & (self.total_df['present_value']>=pv_lower)]
            elif isinstance(pv_lower, int) == True:
                self.total_df = self.total_df[self.total_df['present_value']>=pv_lower]
            elif isinstance(pv_upper, int) == True:
                self.total_df = self.total_df[self.total_df['present_value']<=pv_upper]

        self.total_df['present_value'] = self.total_df['present_value'].fillna(0.0)
        self.total_df['present_value'] = pd.to_numeric(self.total_df['present_value'], errors='coerce').round(2)


        # 持有年限
        holding_period = self.check_int(base_other.get('holding_period', None))

    def clean_data_sql(self, data):
        result = {'land_data': {}, 'owner_data': {}}
        js_data = data.get('searchForm')

        self.query_list = []
        self.sb_range = data.get('data_type', 'sr')
        json_lb_data = js_data.get(self.json_lbtype)

        (self.t_s_mark_tbname, self.t_s_regno_tbname, 
        self.t_s_sc_tbname, self.t_s_sc_reg_tbname, 
        self.col_set_lbkey,
        self.t_s_pack_tbname, 
        self.t_s_regno_pack_tbname)= self.set_sql_db(self.sql_select_db, sb=self.sb_range)

        # base condition=================================================================
        base_region = json_lb_data.get('region', {})
        base_condition = json_lb_data.get('condition', {})
        base_other = json_lb_data.get('other', {})

        if self.fake_data:
            sql = 'SELECT \
                    T2.city_name, T2.area_name, T2.region_name, T2.lno, \
                    T2.national_land_zone, T2.plan_name, T2.land_zone, T2.urban_name, T2.land_area, T2.land_notice_value, \
                    T2.build_num, T2.owner_type, \
                    T1.regno, T1.reg_date_str, T1.reg_reason_str, T1.name, \
                    T1.uid, T1.uid_tag, T1.address_re, T1.bday, T1.right_str, T1.shared_size, T1.creditors_rights, \
                    T1.is_valid, T1.remove_time \
                    FROM \
                    diablo.t_search_lkeyregnolist T1 \
                    left join diablo.t_search_lmlandlist T2 on T1.lbkey =  T2.lkey \
                    WHERE T1.lbkey like "H_01_0001%" and T1.remove_time is null limit 50 \
                    '
            print('測試資料')
            subscriberecords_qs, headers = get_dba(sql_cmd=sql,db_name=DB_NAME)
            result = self.format_data_layout_fake_data(subscriberecords_qs)
        else:
            # vvip 搜尋優化 條件只下行政區====================================
            st1 = time.perf_counter()
            area = base_region.get('area', None)
            section = base_region.get('section', None)
            if section:
                self.query_list.append('and T2.lkey like "{}%"'.format(section))
            elif area:
                self.query_list.append('and T2.lkey like "{}%"'.format(area))
            sql = self.sql_str_combin(self.query_list)
            # print(sql)
            subscriberecords_qs, headers = get_dba(sql_cmd=sql, db_name=DB_NAME)
            st2 = time.perf_counter()
            print(f'sql時間: {st2-st1} 搜尋總筆數:{len(subscriberecords_qs)}')
            # ============================================================
            if not subscriberecords_qs:
                return result
            # df預處理
            self.total_df = pd.DataFrame(subscriberecords_qs)
            self.total_df = self.total_df[self.total_df['is_valid'] != 0]
            self.total_df = self.total_df[pd.isna(self.total_df['remove_time'])==True]
            self.total_df = self.total_df.dropna(subset=['regno'], axis=0, how='any')
            # self.total_df = self.total_df.dropna(subset=['name'], axis=0, how='any')
            self.total_df['plan_name'] = self.total_df['plan_name'].fillna('')
            self.total_df['land_zone_code'] = self.total_df['land_zone_code'].fillna('')
            if self.total_df.empty:
                return result
            new_total_df = self.total_df.copy()
            new_total_df = new_total_df.groupby('lbkey')
            lbkey_dict = new_total_df.size().to_dict()
            self.total_df['owner_num_real'] = self.total_df.apply(self.apply_owners_num, axis=1, args=(lbkey_dict, ))

            #######
            print(f'df預處理後 ：{len(self.total_df)}')

            self.clean_region_data(base_region=base_region)            
            print(f'clean_region_data 處理後 ：{len(self.total_df)}')

            self.clean_condition_data(base_condition)
            print(f'clean_condition_data 處理後 ：{len(self.total_df)}')

            self.clean_other_data(base_other=base_other)
            print(f'clean_other_data 處理後 ：{len(self.total_df)}')

            print(f'輸出總筆數：{len(self.total_df)}')

            fillna_str = ['bday', 'national_land_zone', 'remove_time', 'land_zone_code']
            fillna_zero = ['land_area', 'shared_size', 'build_num']
            self.total_df[fillna_zero] = self.total_df[fillna_zero].fillna(0)
            self.total_df[fillna_str] = self.total_df[fillna_str].fillna('')
            self.total_df = self.total_df.fillna(0)
            result = self.format_data_layout(self.total_df)
        return result

    @extend_schema(
        summary='搜尋',
        description='''''',
        request=GetSearchSerializer,
        responses={
            200: OpenApiResponse(description='處理成功'),
            401: OpenApiResponse(description='身分認證失敗'),
            },
        )
    def post(self, request, *args, **kwargs):
        result = {}
        serializer = GetSearchSerializer(data=request.data)
        if not serializer.is_valid():
            raise ParseError('格式錯誤')
        else:
            # 預設參數
            self.df_delete_column_list = ['reg_reason', 'right_type', 'owners_num', 'case_type', 'restricted_type', 'urban_type', 'remove_time']

            try:
                max_data = info_config.objects.get(lbtype='Max')
                self.max_int = int(max_data.last_info_id)
                self.data_limit = f'LIMIT {self.max_int}'
            except Exception as e:
                print(e)
                self.max_int = 99999
                self.data_limit = f'LIMIT {self.max_in}'

            self.lbtype = serializer.data.get('lbtype')
            if self.lbtype == 'L':
                self.sql_select_db = 'L'
                self.json_lbtype = 'land'
            else:
                self.sql_select_db = 'B'
                self.json_lbtype = 'build'
            self.fake_data = serializer.data.get('fake_data')

            qt1 = time.perf_counter()
            qs_msg = self.clean_data_sql(serializer.data)
            result.update(qs_msg)
            qt2 = time.perf_counter()
            print(f'查詢總時間 : {qt2 - qt1}')
        return Response(result)
