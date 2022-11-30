import json
import logging
import requests
import time
import pandas as pd
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.generic.base import TemplateView, View
from rest_framework import authentication, permissions, serializers
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError
from rest_framework.response import Response

from v_search.serializers import PlanNameSerializer

from v_search.util import CustomJsonEncoder, get_dba
from t_search.models import info_config

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
            if settings.DEBUG == True:
                debug = True
        context['debug'] = debug
        return context

class GetPlanNameView(APIView):
    authentication_classes = [authentication.SessionAuthentication]  #authentication.TokenAuthentication, 
    permission_classes = [permissions.AllowAny] # permissions.IsAuthenticated

    def process(self, datas):
        name_res, nickname_res = [], []
        area = datas.get('area')
        sql = f"SELECT T1.lbkey, T2.plan_name, T2.nickname \
                FROM diablo.t_search_landdevelopementlkeyslist T1 LEFT JOIN diablo.t_search_landdevelopementlist T2 on T1.plan_id = T2.plan_id \
                WHERE  T2.valid =1 and lbkey LIKE '{area}%' \
                "
        res, col = get_dba(sql_cmd=sql, db_name='diablo_test')
        data_df = pd.DataFrame(res)
        if data_df.empty:
            pass
        else:
            # print(data_df)
            group_name = data_df['plan_name'].to_list()
            name_res = list(set(group_name))
            group_nickname = data_df['nickname'].to_list()
            nickname_res = list(set(group_nickname))
        return name_res, nickname_res

    def post(self, request):
        result = {}
        serializer = PlanNameSerializer(data=request.data)
        if serializer.is_valid():
            name_res, nickname_res = self.process(request.data)
            result['plan_name'] = name_res
            result['nick_name'] = nickname_res
        return Response(result)





class GetSearchResponseV3View(APIView):
    authentication_classes = [authentication.TokenAuthentication, authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    TAG = "[GetSearchResponseV3View]"

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

    def check_int(self, num):        
        if isinstance(num, (int, float)) == True:
            return num
        elif isinstance(num, str) == True:
            num = eval(num)
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
                            s1 = '{}-0000'.format(rl_star)
                            s2 = '{}-9999'.format(rl_star)
                            stt = (s1, s2)
                            star_list.append(stt)

                    elif region.find('*') == -1:
                        if region.find('-') != -1:
                            re_reg = region.split('-')
                            a01 = re_reg[0].rjust(4, '0')
                            a02 = re_reg[1].rjust(4, '0')
                            r_str = '{}-{}'.format(a01, a02)
                            result_list.append(r_str)
                        else:
                            b01 = region.rjust(4, '0')
                            br_str = '{}-0000'.format(b01)
                            result_list.append(br_str)
        return result_list, star_list

    def clean_land_data(self, land_data, base_condition, base_other):
        # 總清單
        land_qs_list = []

        if land_data:

            # 選擇地區            
            area = land_data.get('area', None)
            section = land_data.get('section', None)
            if section:
                land_qs_list.append('and T1.lbkey like "{}%"'.format(section))
            elif area:
                land_qs_list.append('and T1.lbkey like "{}%"'.format(area))
            else:
                pass

            # 計畫區
            plan = land_data.get('plan', None)
            if plan:
                land_qs_list.append('and T2.plan_name like "%%{}%%"'.format(plan))

            is_valid = land_data.get('includeInvalid', None)
            # print(is_valid, type(is_valid))
            if is_valid == 1:
                pass
            else:                
                land_qs_list.append('and T1.remove_time is null')

            # 地號子母號
            dataType = self.check_int((land_data.get('dataType', None)))

            # 單筆
            if dataType == 0:
                d_single = land_data.get('landNumberSingle', None)
                fsl = []
                result_list, star_list = self.re_regionV2(d_single)
                if result_list:
                    rel = []
                    for re_reg in result_list:
                        a1 = '"{}"'.format(re_reg)
                        rel.append(a1)
                    fin = ','.join(rel)
                    fst_1 = 'T2.lno in ({})'.format(fin)
                    fsl.append(fst_1)
                if star_list:
                    st_list = []
                    for reg in star_list:
                        if isinstance(reg, tuple):
                            bt1 = reg[0]
                            bt2 = reg[1]
                            st = '(T2.lno between "{}" and "{}")'.format(bt1, bt2)
                            st_list.append(st)
                    fst_2 = ' or '.join(st_list)
                    fsl.append(fst_2)
                if fsl:
                    fsr = ' or '.join(fsl)
                    land_qs_list.append('and ({})'.format(fsr))

            # 多筆
            elif dataType == 1:
                # print('多筆')
                d_Multiple = land_data.get('landNumberMultiple', None)
                fsl = []
                result_list, star_list = self.re_regionV2(d_Multiple)
                if result_list:
                    rel = []
                    for re_reg in result_list:
                        a1 = '"{}"'.format(re_reg)
                        rel.append(a1)
                    fin = ','.join(rel)
                    fst_1 = 'T2.lno in ({})'.format(fin)
                    fsl.append(fst_1)
                if star_list:
                    st_list = []
                    for reg in star_list:
                        if isinstance(reg, tuple):
                            bt1 = reg[0]
                            bt2 = reg[1]
                            st = '(T2.lno between "{}" and "{}")'.format(bt1, bt2)
                            st_list.append(st)
                    fst_2 = ' or '.join(st_list)
                    fsl.append(fst_2)
                if fsl:
                    fsr = ' or '.join(fsl)
                    land_qs_list.append('and ({})'.format(fsr))

            # 區間
            elif dataType == 2:
                try:
                    d_Multiple_L = land_data.get('landNumberLowerLimit', None)
                    d_Multiple_U = land_data.get('landNumberUpperLimit', None)
                    low = self.re_regionV2(d_Multiple_L)[0][0]
                    up = self.re_regionV2(d_Multiple_U)[0][0]
                    if low and up:                    
                        land_qs_list.append('and T2.lno between "{llo}" and "{uup}"'.format(llo=low, uup=up))
                except:
                    pass

            # 特別分類 面積分類 總 持分 平均持分 ==========================
            areaType = self.check_int(base_condition.get('areaType'))
            l_lower = self.check_int(base_condition.get('landAreaLowerLimit', None))
            l_upper = self.check_int(base_condition.get('landAreaUpperLimit', None))
            if isinstance(l_lower, (int, float)):
                l_lower = l_lower / 0.3025
                l_lower = round(l_lower, 4)
            if isinstance(l_upper, (int, float)):
                l_upper = l_upper / 0.3025
                l_upper = round(l_upper, 4)

            # 面積
            try:
                if l_lower == 0 and l_upper == 0:
                    pass
                else:
                    if areaType == 0:                    
                        if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                            if l_lower == 0 and l_upper == 0:
                                pass
                            else:
                                land_qs_list.append('and T2.land_area >= {l} and T2.land_area <= {u}'.format(l=l_lower, u=l_upper))

                        elif isinstance(l_lower, (int, float)) == True:
                            land_qs_list.append('and T2.land_area >= {}'.format(l_lower))
                        elif isinstance(l_upper, (int, float)) == True:
                            land_qs_list.append('and T2.land_area <= {}'.format(l_upper))

                    elif areaType == 1:  
                        if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                            if l_lower == 0 and l_upper == 0:
                                pass
                            else:
                                land_qs_list.append('and T1.shared_size >= {l} and T1.shared_size <= {u}'.format(l=l_lower, u=l_upper))

                        elif isinstance(l_lower, (int, float)) == True:
                            land_qs_list.append('and T1.shared_size >= {}'.format(l_lower))
                        elif isinstance(l_upper, (int, float)) == True:
                            land_qs_list.append('and T1.shared_size <= {}'.format(l_upper))
                        else:
                            pass

                    elif areaType == 2:
                        try:
                            self.math_str = [', (T2.land_area / T2.owners_num) as common_part']
                            if isinstance(l_lower, (int, float)) == True and isinstance(l_upper, (int, float)) == True:
                                if l_lower == 0 and l_upper == 0:
                                    pass
                                else:
                                    self.math_str.append('HAVING(common_part > {l} and common_part < {u})'.format(l=l_lower, u=l_upper))
                            elif isinstance(l_lower, (int, float)) == True:
                                self.math_str.append('HAVING(common_part >= {})'.format(l_lower))
                            elif isinstance(l_upper, (int, float)) == True:
                                self.math_str.append('HAVING(common_part <= {})'.format(l_upper))
                            else:
                                self.math_str = None
                        except Exception as e:
                            print(e)
            except Exception as e:
                print(e)

            # 使用區分類
            land_zone_type = self.check_int(base_condition.get('useSection', None))
            lz_list = []
            lz_qs = []
            us_or_list = []
            if land_zone_type == 0:                
                pass
            elif land_zone_type == 1:
                land_qs_list.append('and T2.urban_type = 1')
                lz_list = [self.use_zone_re(x) for x in base_condition.get('inCity', None)]

            elif land_zone_type == 2:
                land_qs_list.append('and T2.urban_type = 2')
                lz_list = [self.use_zone_re(x) for x in base_condition.get('outCity', None)]
            else:
                pass

            if lz_list:
                if len(lz_list) == 1:
                    land_qs_list.append('and T2.land_zone like "%%{}%%"'.format(lz_list[0]))
                else:
                    for us_str in lz_list:
                        all_us = 'T2.land_zone like "%%{uss}%%"'.format(uss=us_str)
                        us_or_list.append(all_us)
            if us_or_list:
                or_str = ' or '.join(us_or_list)
                land_qs_list.append('and ({})'.format(or_str))

            # 是否有地上建物
            isBuild = self.check_int(base_condition.get('isBuild', None))
            if isBuild == -1:
                pass
            elif isBuild == 0:
                land_qs_list.append('and T2.build_num = 0')
            elif isBuild == 1:
                land_qs_list.append('and T2.build_num > 0')

            # 地上建物型態
            build_type = self.check_int(base_condition.get('buildType', None))
            if build_type == 0:
                pass
            elif isinstance(build_type, int) == True:
                land_qs_list.append('and T2.build_type = {}'.format(build_type))

            # 屋齡
            building_age = base_condition.get('houseAge', None)
            if building_age:
                if len(building_age) == 1:
                    building_age_int  = self.check_int(building_age[0])
                    set_build_age = self.yearsagoV2(building_age_int)
                    if building_age_int < 20:
                        land_qs_list.append('and T2.build_finish_time >= "{}"'.format(set_build_age))
                    else:
                        land_qs_list.append('and T2.build_finish_time <= "{}"'.format(set_build_age))
                else:
                    set_build_age_low = self.yearsagoV2(self.check_int(building_age[1]))
                    set_build_age_up = self.yearsagoV2(self.check_int(building_age[0]))
                    if set_build_age_low and set_build_age_up:
                        land_qs_list.append('and T2.build_finish_time >= "{}"'.format(set_build_age_low))
                        land_qs_list.append('and T2.build_finish_time <= "{}"'.format(set_build_age_up))
                    elif set_build_age_up == None and set_build_age_low != None:
                        land_qs_list.append('and T2.build_finish_time >= "{}"'.format(set_build_age_low))

        return land_qs_list

    def clean_build_data(self, build_data, base_condition, base_other):
        # 總清單
        build_qs_list = []

        if build_data:
            # 地區
            section = build_data.get('area', None)
            if section:
                build_qs_list.append('and T2.bkey like "%%{}%%"'.format(section))
            # 社區
            community = build_data.get('community', None)
            if community:
                build_qs_list.append('and T2.community_name like "%%{}%%"'.format(community))

            # 路名
            road = build_data.get('road')
            if road:
                build_qs_list.append('and T2.road_name like "%%{}%%"'.format(road))

            is_valid = build_data.get('includeInvalid', None)
            # print(is_valid, type(is_valid))
            if is_valid == 1:
                pass
            else:
                build_qs_list.append('and T1.remove_time is null')

            # 面積 建物只有總面積
            b_lower = self.check_int(base_condition.get('buildAreaLowerLimit'))
            b_upper = self.check_int(base_condition.get('buildAreaUpperLimit'))
            if b_lower == 0 and b_upper == 0:
                pass
            else:
                if isinstance(b_lower, (int, float)):
                    b_lower = b_lower / 0.3025
                    b_lower = round(b_lower, 4)
                if isinstance(b_upper, (int, float)):
                    b_upper = b_upper / 0.3025
                    b_upper = round(b_upper, 4)

                if isinstance(b_lower, (int, float)) == True and isinstance(b_upper, (int, float)) == True:
                    build_qs_list.append('and T2.build_size >= {low} and T2.build_size <= {up}'.format(low=b_lower, up=b_upper))
                elif isinstance(b_lower, (int, float)) == True:
                    build_qs_list.append('and T2.build_size >= {}'.format(b_lower))
                elif isinstance(b_upper, (int, float)) == True:
                    build_qs_list.append('and T2.build_size <= {}'.format(b_upper))
            
            # 建物層次
            b_f_low = self.check_int(base_condition.get('buildFloorLowerLimit'))
            b_f_upp = self.check_int(base_condition.get('buildFloorUpperLimit'))
            if b_f_low == 0 and b_f_upp == 0:
                pass
            else:
                if isinstance(b_f_low, int) == True and isinstance(b_f_upp, int) == True:
                    build_qs_list.append('and T2.floor_first >= {first} and T2.floor_last <= {last}'.format(first=b_f_low, last=b_f_upp))
                elif isinstance(b_f_low, int):
                    build_qs_list.append('and T2.floor_first >= {}'.format(b_f_low))
                elif isinstance(b_f_upp, int):
                    build_qs_list.append('and T2.floor_last <= {}'.format(b_f_upp))

            # 屋齡
            build_age_low = self.check_int(base_condition.get('buildAgeLowerLimit', None))
            build_age_upp = self.check_int(base_condition.get('buildAgeUpperLimit', None))
            if build_age_low == 0 and build_age_upp == 0:
                pass
            else:
                b_a_low = self.yearsagoV2(build_age_low)
                b_a_upp = self.yearsagoV2(build_age_upp)
                if b_a_low and b_a_upp:
                    build_qs_list.append('and T2.finish_time between "{lo}" and "{up}"'.format(lo=b_a_upp, up=b_a_low))
                elif b_a_low != None:
                    build_qs_list.append('and T2.finish_time <= "{}"'.format(b_a_low))
                elif b_a_upp != None:
                    build_qs_list.append('and T2.finish_time >= "{}"'.format(b_a_upp))

            # 主要用途
            main_purpose = base_condition.setdefault('houseUse', {})
            use_key = [x for x, y in main_purpose.items() if y != 0]
            mp_list = []
            for i in use_key:
                j = self.main_purpose_dict.get(i)
                if j:
                    mp_list.append(j)
            if mp_list:
                build_qs_list.append('and T2.main_purpose in ({})'.format(','.join(mp_list)))

            # 建物型態
            build_type = base_condition.get('buildType', None)
            if build_type:
                if build_type == 0:
                    pass
                else:
                    build_qs_list.append('and build_type = {}'.format(build_type))
        return build_qs_list

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

    def sql_str_combin(self, condition_list):
        # base sql
                    # {col}
        sql_str =  "\
                    SELECT {col} \
                    {math_s} \
                    FROM \
                    diablo.{tr1} T1 \
                    left join diablo.{t2} T2 on T1.lbkey =  T2.{lbk} \
                    WHERE {where_sql} {having} limit 500000 \
                    "

        condition = ''
        if condition_list:
            for ind, i in enumerate(condition_list):
                if ind == 0:
                    i = i.replace('and', '')
                condition += f' {i}'

        qs_F = ''
        hav = ''
        if self.math_str:
            qs_F = self.math_str[0]
            hav = self.math_str[1]

        # 欄位後面要空格 換行要加斜線
        if self.json_lbtype == 'land':
            select_colunm = "\
                            T1.id, T1.regno, T1.remove_time, T1.property_type, \
                            T2.plan_name, T2.land_zone, T2.urban_name, 2.land_notice_value, \
                            T2.build_num, T2.land_area, T2.other_remark, T2.national_land_zone, \
                            T1.reg_reason_str, T1.reg_date_str, T1.name, T1.uid, T1.address_re, T1.right_str, T1.shared_size, \
                            T1.creditors_rights, T1.is_valid \
                            "
        # 欄位後面要空格 換行要加斜線
        else:
            select_colunm = "\
                            T1.id, T1.regno, T1.remove_time, T1.property_type, \
                            T2.road_name_re, T2.community_name, T2.door, T2.main_purpose, T2.finish_day, T2.total_level, T2.build_size, \
                            T1.reg_reason_str, T1.reg_date_str, T1.name, T1.uid, \
                            T1.address_re, T1.right_str, T1.shared_size, \
                            T1.creditors_rights, T1.is_valid \
                            "

        sql = sql_str.format(
                            col=select_colunm,
                            math_s = qs_F,
                            tr1 = self.t_s_regno_tbname,
                            t2 = self.t_s_mark_tbname,
                            lbk = self.col_set_lbkey,
                            where_sql = condition,
                            having = hav,
                            limit = self.data_limit)
        print(sql)
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

    def clean_data_sql(self, data):
        result = {'status':'NG', 'msg':''}
        if data:
            try:
                js_data = json.loads(data.get('searchForm'))
            except Exception as e:
                print(e)
                result['msg'] = '請確認 key "searchForm" 型態是否正確'
                js_data = {}
                return result

            try:
                com_sql_t1 = time.perf_counter()
                query_list = []
                lbtype = data.get('lbtype')
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
                self.math_str = None

                # 登記原因
                registerReason = self.check_int(base_condition.get('registerReason'))
                if isinstance(registerReason, int) == True:
                    if registerReason == 0:
                        pass
                    else:
                        query_list.append('and T1.reg_reason = {}'.format(str(registerReason)))

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
                        query_list.append('and T2.owner_type in ({})'.format(','.join([str(x) for x in os_list])))

                # 權利範圍型態 (公同共有)
                ownershipType = self.check_int(base_condition.get('ownershipType'))
                if ownershipType:
                    if ownershipType == 0:
                        pass
                    elif ownershipType == 1:
                        query_list.append('and T1.right_type in (0,1,2)')
                    elif ownershipType == 2:
                        query_list.append('and T1.right_type = 3')

                # 所有權人數
                o_num_low = self.check_int(base_condition.get('ownershipNumLowerLimit'))
                o_num_up = self.check_int(base_condition.get('ownershipNumUpperLimit'))
                if o_num_low == 0 and o_num_up == 0:
                    pass
                else:
                    if isinstance(o_num_up, int) == True and isinstance(o_num_low, int) == True:
                        query_list.append('and T2.owners_num <= {num_max} and T2.owners_num >= {num_min}'.format(num_max=o_num_up, num_min=o_num_low))
                    elif isinstance(o_num_low, int) == True:
                        query_list.append('and T2.owners_num >= {num_min}'.format(num_min=o_num_low))
                    elif isinstance(o_num_up, int) == True:
                        query_list.append('and T2.owners_num <= {num_max}'.format(num_max=o_num_up))

                # 他項設定:他項標記
                cast_type = self.check_int(base_other.get('otherRemark', None))
                if cast_type == 0:
                    pass
                else:
                    query_list.append('and T1.case_type = {}'.format(cast_type))

                # 他項設定:限制登記
                restricted_type = self.check_int(base_other.get('restrictedRegistration', None))
                if restricted_type == 0:
                    pass
                else:
                    query_list.append('and T1.restricted_type = {}'.format(restricted_type))
                
                # 土建分開條件
                if lbtype == 'L':
                    qs_merge = self.clean_land_data(base_region, base_condition, base_other)
                    # print(qs_merge)
                else:
                    qs_merge = self.clean_build_data(base_region, base_condition, base_other)
                    # print(qs_merge)
                
                if qs_merge:
                    query_list.extend(qs_merge)
                
                # 資料筆數限制
                try:
                    max_data = info_config.objects.get(lbtype='Max')
                    self.max_int = int(max_data.last_info_id)
                    self.data_limit = 'LIMIT {}'.format(self.max_int) # self.max_int
                except Exception as e:
                    print(e)
                    self.max_int = 99999
                    self.data_limit = 'LIMIT {}'.format(self.max_int)

                sql = self.sql_str_combin(query_list)

                com_sql_t2 = time.perf_counter()
                print('組sql語法時間 : {}'.format(com_sql_t2 - com_sql_t1))

                qs_sql_t1 = time.perf_counter()
                subscriberecords_qs, headers = get_dba(sql, "diablo_test")

                qs_sql_t2 = time.perf_counter()
                print('sql查詢時間 : {}'.format(qs_sql_t2 - qs_sql_t1))
                print(len(subscriberecords_qs))
                # print(subscriberecords_qs[0])
                rb_sql_t1 = time.perf_counter()

                result["status"] = 'OK'
                rb_sql_t2 = time.perf_counter()
                print('組完資料輸出時間 : {}'.format(rb_sql_t2 - rb_sql_t1))

            except Exception as e:
                result['msg'] = e
                print(e)
                return result
        else:
            result['msg'] = '請輸入 data'
        return result


    def process(self, params, request):
        result = {'status':'NG'}
        if params.get('lbtype') == 'L':
            self.sql_select_db = 'L'
            self.json_lbtype = 'land'
        else:
            self.sql_select_db = 'B'
            self.json_lbtype = 'build'

        qs_msg = self.clean_data_sql(params)
        result.update(qs_msg)

        return result

    def post(self, request, *args, **kwargs):
        params = request.POST.copy()
        # self.user = User.objects.get(username=request.user.get_username()).id
        self.user = 664
        print(f'使用者id: {self.user}')
        st1 = time.perf_counter()
        result = self.process(params, request)
        en1 = time.perf_counter()
        print('查詢總時間 : {}'.format(en1 - st1))
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")

