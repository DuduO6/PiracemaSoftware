from rest_framework import serializers
from .models import Viagem

class ViagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Viagem
        fields = '__all__'
        read_only_fields = ['usuario', 'valor_total']
