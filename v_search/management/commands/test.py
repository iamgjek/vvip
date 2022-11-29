import logging
import time
import os

import pandas as pd
from django.core.management.base import BaseCommand

from v_search.util import get_dba
from t_search.models import info_config

logger = logging.getLogger(__name__)



class Command(BaseCommand):
    """
    test
    """
    help = 'test'
    
    def handle(self, *args, **options):
        res = info_config.objects.get(id=1)
        print(res.lbtype)







