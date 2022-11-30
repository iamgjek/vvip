from rest_framework import serializers



class PlanNameSerializer(serializers.Serializer):
    area = serializers.CharField(default="", help_text='A_01', min_length=4, max_length=4)


