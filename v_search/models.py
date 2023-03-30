from django.db import models

class LBkeyClassification(models.Model):
    lbkey = models.CharField(max_length=19, primary_key=True, verbose_name='地建號')
    rank = models.CharField(max_length=1, null=True, blank=True, verbose_name='等級')
    update_time = models.DateTimeField(auto_now=True, null=False, blank=False, verbose_name='最後設定時間')

    class Meta:
        verbose_name = "地建號等級標示"
        verbose_name_plural = "地建號等級標示"
        indexes = [
            models.Index(fields=['rank']),
        ]