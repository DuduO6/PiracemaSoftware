from rest_framework import serializers


class SeguroCargasCalculoSerializer(serializers.Serializer):
    origem = serializers.CharField(required=True, max_length=100)
    destino = serializers.CharField(required=True, max_length=100)
    valor_rctr_c = serializers.DecimalField(required=True, min_value=0, decimal_places=2, max_digits=14)
    valor_rcdc = serializers.DecimalField(required=True, min_value=0, decimal_places=2, max_digits=14)

    def validate(self, attrs):
        if attrs["valor_rctr_c"] == 0 and attrs["valor_rcdc"] == 0:
            raise serializers.ValidationError(
                "Informe ao menos um valor de carga maior que zero para realizar o cálculo."
            )
        return attrs

