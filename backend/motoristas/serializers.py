from rest_framework import serializers
from .models import DescontoVale, Motorista, Vale


class DescontoValeSerializer(serializers.ModelSerializer):
    acerto_periodo = serializers.SerializerMethodField()

    class Meta:
        model = DescontoVale
        fields = ["id", "data", "valor", "saldo_antes", "saldo_depois", "acerto", "acerto_periodo"]

    def get_acerto_periodo(self, obj):
        if not obj.acerto_id:
            return None
        return {
            "data_inicio": obj.acerto.data_inicio,
            "data_fim": obj.acerto.data_fim,
        }


class ValeSerializer(serializers.ModelSerializer):
    descontos = DescontoValeSerializer(many=True, read_only=True)

    class Meta:
        model = Vale
        fields = "__all__"
        read_only_fields = ["valor_descontado"]

    def create(self, validated_data):
        if not validated_data.get("valor_original"):
            validated_data["valor_original"] = validated_data.get("valor", 0)
        return super().create(validated_data)


class MotoristaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # carregar vales automaticamente
    vales = ValeSerializer(many=True, read_only=True)

    class Meta:
        model = Motorista
        fields = "__all__"
