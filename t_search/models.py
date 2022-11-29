from django.db import models

class info_config(models.Model):
    last_info_id = models.IntegerField(null=True, blank=True, verbose_name='最後一筆情資id')
    lbtype = models.CharField(max_length=10, null=True, blank=True, verbose_name='lbtype')
    comment = models.TextField(blank=True, null=True, verbose_name='comment')
    create_time = models.DateTimeField(null=True, blank=True, verbose_name='新增時間')
    class Meta:
        managed = False
        db_table = 't_search_info_config'


