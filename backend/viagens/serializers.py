from decimal import Decimal

from rest_framework import serializers
from .models import Viagem


class ViagemSerializer(serializers.ModelSerializer):
    valor_total_informado = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        write_only=True,
    )

    class Meta:
        model = Viagem
        fields = '__all__'
        read_only_fields = ['usuario', 'valor_total']
        extra_kwargs = {
            "valor_tonelada": {"required": False},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)

        peso = attrs.get("peso", getattr(self.instance, "peso", None))
        valor_tonelada = attrs.get("valor_tonelada")
        valor_total_informado = attrs.pop("valor_total_informado", None)

        if peso in (None, 0):
            raise serializers.ValidationError({"peso": "Informe um peso válido para calcular o frete."})

        if valor_tonelada and valor_total_informado:
            raise serializers.ValidationError(
                {"non_field_errors": ["Informe apenas o valor por tonelada ou o valor total do frete."]}
            )

        if valor_total_informado is not None:
            attrs["valor_tonelada"] = valor_total_informado / peso
            return attrs

        if valor_tonelada is not None:
            return attrs

        if self.instance:
            return attrs

        raise serializers.ValidationError(
            {"non_field_errors": ["Informe o valor por tonelada ou o valor total do frete."]}
        )


class AvaliadorViagemSerializer(serializers.Serializer):
    viagem_id = serializers.IntegerField(required=True, min_value=1)
    media_km_por_litro = serializers.DecimalField(
        required=True, max_digits=8, decimal_places=2, min_value=Decimal("0.01")
    )
    preco_combustivel = serializers.DecimalField(
        required=True, max_digits=8, decimal_places=2, min_value=Decimal("0.01")
    )
    cidade_origem = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
    estado_origem = serializers.CharField(required=False, allow_blank=True, max_length=2, default="")
    cidade_destino = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
    estado_destino = serializers.CharField(required=False, allow_blank=True, max_length=2, default="")
