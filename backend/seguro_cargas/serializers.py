from rest_framework import serializers


class SeguroCargasCalculoSerializer(serializers.Serializer):
    origem = serializers.CharField(required=True, max_length=100)
    destino = serializers.CharField(required=True, max_length=100)
    valor_carga = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14)
    # Compatibilidade com a tela anterior. Quando valor_carga não é enviado,
    # ambos continuam alimentando o cálculo original da planilha.
    valor_rctr_c = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14)
    valor_rcdc = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14)
    multiplicador = serializers.DecimalField(required=False, min_value=0, decimal_places=4, max_digits=10, default="2")
    acrescimo_fixo = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14, default="6")
    piso_comercial = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14, default="30")
    proporcao_rctrc = serializers.DecimalField(required=False, min_value=0, max_value=100, decimal_places=4, max_digits=7, default="50")
    precisao_percentual = serializers.IntegerField(required=False, min_value=1, max_value=10, default=6)
    percentual_rctrc_manual = serializers.DecimalField(required=False, min_value=0, decimal_places=10, max_digits=18, allow_null=True)
    percentual_rcdc_manual = serializers.DecimalField(required=False, min_value=0, decimal_places=10, max_digits=18, allow_null=True)
    taxa_real_rctrc = serializers.DecimalField(required=False, min_value=0, decimal_places=10, max_digits=18, allow_null=True)
    taxa_real_rcdc = serializers.DecimalField(required=False, min_value=0, decimal_places=10, max_digits=18, allow_null=True)
    piso_minimo_antt = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14, default="0")
    margem_adicional = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14, default="200")
    pedagio = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14, default="0")
    outras_despesas = serializers.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=14, default="0")

    def validate(self, attrs):
        valor_carga = attrs.get("valor_carga")
        valor_rctr_c = attrs.get("valor_rctr_c")
        valor_rcdc = attrs.get("valor_rcdc")

        if valor_carga is None:
            if valor_rctr_c is None or valor_rcdc is None:
                raise serializers.ValidationError("Informe o valor total da carga.")
            valor_carga = max(valor_rctr_c, valor_rcdc)
            attrs["valor_carga"] = valor_carga

        if valor_carga == 0:
            raise serializers.ValidationError(
                "O valor total da carga deve ser maior que zero para realizar o cálculo."
            )

        attrs.setdefault("valor_rctr_c", valor_carga)
        attrs.setdefault("valor_rcdc", valor_carga)

        manual_rctrc = attrs.get("percentual_rctrc_manual")
        manual_rcdc = attrs.get("percentual_rcdc_manual")
        if (manual_rctrc is None) != (manual_rcdc is None):
            raise serializers.ValidationError(
                "Informe os dois percentuais manuais ou deixe ambos em branco."
            )
        return attrs

