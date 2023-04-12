import copy
import json
import logging
import sys
import time
from datetime import date, datetime

import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import HttpResponseRedirect
from django.utils import timezone
from django.views import View
from django.views.generic.base import TemplateView
from wsos_common.utility import getLBType
from v_search.util import CustomJsonEncoder, get_dba

logger = logging.getLogger(__name__)
DB_NAME = 'diablo_test'

class GetRecnoRangeView(View):
    TAG = '[GetRecnoRangeView]'

    def process(self, request):
        result = {'status': 'NG', 'msg': 'error'}
        try:
            params = request.POST
            lon = params.get('lon', None)
            lat = params.get('lat', None)
            dis = params.get('dis', 500)
            if not lon:
                result['msg'] = '請輸入經度'
                return result
            if not lat:
                result['msg'] = '請輸入緯度'
                return result
            lon = float(lon)
            lat = float(lat)
            dis = int(dis) * 0.00001
            sql = f'''SELECT *, ST_AsGeoJSON(point) as point, (ST_Distance(POINT({lon},{lat}) ,point) * 100000) as distance
                        FROM diablo.lvr_land_recnolist
                        where point is not null and (ST_Distance(POINT({lon},{lat}), point)) <= {dis}
                        order by distance
                        '''
            # dis = int(dis)
            # sql = f'''SELECT *, ST_AsGeoJSON(point) as point, (ST_Distance_Sphere(point, POINT({lon},{lat}))) as distance
            #             FROM diablo.lvr_land_recnolist
            #             where (ST_Distance_Sphere(point, POINT({lon},{lat}))) <= {dis}
            #             '''
            print(sql)
            subscriberecords_qs, headers = get_dba(sql_cmd=sql,db_name=DB_NAME)
            # print(subscriberecords_qs)
            result['status'] = 'OK'
            result['msg'] = '成功傳送資料'
            result['datas'] = subscriberecords_qs
        except Exception as e:
            logger.info(f'錯誤訊息：{e}，錯誤行數：{sys.exc_info()[2].tb_lineno}')
        return result

    def post(self, request):
        logger.info('取得範圍內實價資料')
        time_start = time.perf_counter()
        result = self.process(request)
        time_end = time.perf_counter()
        logger.info(f'花費時間：{time_end - time_start}秒')
        if 'status' in result and result['status'] == 'NG':
            return HttpResponseBadRequest(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type="application/json; charset=utf-8")
        return HttpResponse(json.dumps(result, ensure_ascii=False, cls=CustomJsonEncoder), content_type='application/json; charset=utf-8')