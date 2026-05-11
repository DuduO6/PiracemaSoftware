from decimal import Decimal, ROUND_HALF_UP

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

    def _normalize_text(self, value):
        return " ".join(str(value or "").strip().upper().split())

    def _get_valor_total(self, attrs):
        peso = attrs.get("peso", getattr(self.instance, "peso", None))
        valor_tonelada = attrs.get("valor_tonelada", getattr(self.instance, "valor_tonelada", None))
        teve_cte = attrs.get("teve_cte", getattr(self.instance, "teve_cte", False))
        if peso is None or valor_tonelada is None:
            return None
        valor_total = peso * valor_tonelada
        if teve_cte:
            valor_total *= Decimal("0.90")
        return valor_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _get_duplicate_queryset(self, attrs):
        request = self.context.get("request")
        usuario = getattr(request, "user", None) or getattr(self.instance, "usuario", None)
        if not usuario or not getattr(usuario, "is_authenticated", False):
            return Viagem.objects.none()

        motorista = attrs.get("motorista", getattr(self.instance, "motorista", None))
        data = attrs.get("data", getattr(self.instance, "data", None))
        peso = attrs.get("peso", getattr(self.instance, "peso", None))
        valor_tonelada = attrs.get("valor_tonelada", getattr(self.instance, "valor_tonelada", None))

        if not all([motorista, data, peso, valor_tonelada]):
            return Viagem.objects.none()

        queryset = Viagem.objects.filter(
            usuario=usuario,
            motorista=motorista,
            data=data,
            peso=peso,
            valor_tonelada=valor_tonelada,
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        return queryset

    def get_duplicate_trip(self, attrs):
        origem = self._normalize_text(attrs.get("origem", getattr(self.instance, "origem", "")))
        destino = self._normalize_text(attrs.get("destino", getattr(self.instance, "destino", "")))
        cliente = self._normalize_text(attrs.get("cliente", getattr(self.instance, "cliente", "")))
        teve_cte = attrs.get("teve_cte", getattr(self.instance, "teve_cte", False))
        numero_cte = self._normalize_text(attrs.get("numero_cte", getattr(self.instance, "numero_cte", "")))
        valor_total = self._get_valor_total(attrs)

        for viagem in self._get_duplicate_queryset(attrs):
            if (
                self._normalize_text(viagem.origem) == origem
                and self._normalize_text(viagem.destino) == destino
                and self._normalize_text(viagem.cliente) == cliente
                and viagem.teve_cte == teve_cte
                and self._normalize_text(viagem.numero_cte) == numero_cte
                and (valor_total is None or viagem.valor_total == valor_total)
            ):
                return viagem
        return None

    def build_duplicate_warning(self, attrs):
        viagem = self.get_duplicate_trip(attrs)
        if not viagem:
            return None

        return {
            "duplicada": True,
            "detail": "Possível duplicidade: já existe uma viagem anterior com os mesmos dados principais.",
            "viagem_id": viagem.id,
            "data": viagem.data.isoformat(),
            "origem": viagem.origem,
            "destino": viagem.destino,
            "cliente": viagem.cliente,
            "valor_total": f"{viagem.valor_total:.2f}",
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)

        peso = attrs.get("peso", getattr(self.instance, "peso", None))
        valor_tonelada = attrs.get("valor_tonelada")
        valor_total_informado = attrs.pop("valor_total_informado", None)
        teve_cte = attrs.get("teve_cte", getattr(self.instance, "teve_cte", False))
        numero_cte = (attrs.get("numero_cte", getattr(self.instance, "numero_cte", "")) or "").strip()

        attrs["numero_cte"] = numero_cte

        if peso in (None, 0):
            raise serializers.ValidationError({"peso": "Informe um peso válido para calcular o frete."})

        if teve_cte and not numero_cte:
            raise serializers.ValidationError({"numero_cte": "Informe o número do CT-e."})

        if not teve_cte:
            attrs["numero_cte"] = ""

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
