import ast
import copy
import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import requests
import urllib3
from django.conf import settings
from django.db import (close_old_connections, connection, connections, models,
                       reset_queries)
from django.db.models.fields.files import ImageFieldFile
from django.utils import timezone
from openpyxl.utils import get_column_letter
from wsos_common.enums import LB_TYPE
from wsos_common.utility import getLBType

logger = logging.getLogger(__name__)
max_dba_retries = 3

# 都內使用分區
IN_CITY_USEZONE = ["工業區", "文教區", "水岸發展區", "水域", "行水區", "行政區", "住宅區", "別墅區", "防風林區", "其他使用分區", "服務區", "林業區", "河川區", "保存區", "保護區", "活動區", "風景區", "倉庫區", "旅館區", "海濱浴場區", "動植物園區", "商業區", "國家公園區", "眺望區", "野餐區", "魚塭區", "景觀區", "溫泉區", "葬儀業區", "農業區", "遊樂區", "遊憩區", "漁業區", "營區", "露營區", "體育運動", "鹽田區", "觀光農場區"]
# 都外使用分區
OUT_CITY_USEZONE = ["特定農業區", "一般農業區", "工業區", "鄉村區", "森林區", "山坡地保護區", "風景區", "國家公園區", "河川區", "海域區", "其他使用區或特定專區"]
# 都外使用地類別
OUT_CITY_URBAN_NAME = ["甲種建築用地", "乙種建築用地", "丙種建築用地", "丁種建築用地", "牧農用地", "林業用地", "養殖用地", "鹽業用地", "礦業用地", "窯業用地", "交通用地", "水利用地", "遊憩用地", "古蹟保存用地", "生態保護用地", "國土保安用地", "殯葬用地", "海域用地", "特定目的事業用地"]
# 國土分區
COUNTRY_LAND_ZONE = ["全部", "城一", "城二之一", "城二之二", "城二之三", "城三", "農一", "農二", "農三", "農四", "國一", "國二", "國三", "國四", "海一之一", "海一之二", "海一之三", "海二", "海三", "未分類"]

def get_dba(sql_cmd, db_name='default', retries=0):
    rows = dict()
    columns = list()
    while retries < max_dba_retries:
        try:
            close_old_connections()
            with connections[db_name].cursor() as cursor:
                cursor.execute(sql_cmd)
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                # rows = dictfetchall(cursor)
                cursor.close()
            break
        except Exception as error:
            retries += 1
            print ('{} {} retries {} error: {}'.format(datetime.now(), get_dba.__name__, retries, error))
    return rows, columns

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

