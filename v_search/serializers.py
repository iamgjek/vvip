from rest_framework import serializers



class PlanNameSerializer(serializers.Serializer):
    area = serializers.CharField(default="A_01", help_text='A_01', min_length=4, max_length=4)


class GetSearchSerializer(serializers.Serializer):
    lbtype = serializers.CharField(default="", help_text='')
    searchForm = serializers.JSONField(default=dict, help_text='條件json')
    fake_data = serializers.BooleanField(default=False, help_text='是否取用測試資料')