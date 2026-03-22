from rest_framework import serializers

from .constants import (
    DEFAULT_PESO_ESTIMADO_TONELADAS,
    DEFAULT_QUANTIDADE_EIXOS,
    DEFAULT_TIPO_CARGA,
    DEFAULT_PERCENTUAL_LUCRO_ADICIONAL,
    TIPOS_CARGA,
)


class FreteCalculatorSerializer(serializers.Serializer):
    cidade_origem = serializers.CharField(required=True, max_length=120)
    estado_origem = serializers.CharField(required=False, allow_blank=True, max_length=2, default="")
    cidade_destino = serializers.CharField(required=True, max_length=120)
    estado_destino = serializers.CharField(required=False, allow_blank=True, max_length=2, default="")
    quantidade_eixos = serializers.IntegerField(required=False, min_value=1, default=DEFAULT_QUANTIDADE_EIXOS)
    tipo_carga = serializers.ChoiceField(required=False, choices=[value for value, _ in TIPOS_CARGA], default=DEFAULT_TIPO_CARGA)
    composicao_veicular = serializers.BooleanField(required=False, default=True)
    alto_desempenho = serializers.BooleanField(required=False, default=False)
    retorno_vazio = serializers.BooleanField(required=False, default=False)
    adicionar_lucro_adicional = serializers.BooleanField(required=False, default=False)
    percentual_lucro_adicional = serializers.DecimalField(
        required=False, max_digits=6, decimal_places=2, min_value=0, default=DEFAULT_PERCENTUAL_LUCRO_ADICIONAL
    )
    peso_estimado_toneladas = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0, default=DEFAULT_PESO_ESTIMADO_TONELADAS
    )

    def validate(self, attrs):
        origem = attrs["cidade_origem"].strip().lower()
        destino = attrs["cidade_destino"].strip().lower()
        estado_origem = attrs.get("estado_origem", "").strip().lower()
        estado_destino = attrs.get("estado_destino", "").strip().lower()

        if origem == destino and estado_origem == estado_destino:
            raise serializers.ValidationError("Origem e destino não podem ser iguais.")

        if not attrs.get("adicionar_lucro_adicional"):
            attrs["percentual_lucro_adicional"] = 0

        return attrs
