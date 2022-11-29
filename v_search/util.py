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

# def dictfetchall(cursor):
#     columns = [col[0] for col in cursor.description]
#     return [
#         dict(zip(columns, row))
#         for row in cursor.fetchall()
#     ]

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
