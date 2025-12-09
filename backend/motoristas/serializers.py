from rest_framework import serializers
from .models import Motorista, Vale

class ValeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vale
        fields = "__all__"


class MotoristaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # carregar vales automaticamente
    vales = ValeSerializer(many=True, read_only=True)

    class Meta:
        model = Motorista
        fields = "__all__"
