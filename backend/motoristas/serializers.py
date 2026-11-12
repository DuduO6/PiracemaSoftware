import re

from rest_framework import serializers
from .models import DescontoVale, Motorista, Vale


def _cpf_digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _cpf_is_valid(value):
    digits = _cpf_digits(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    numbers = [int(digit) for digit in digits]
    first_total = sum(number * weight for number, weight in zip(numbers[:9], range(10, 1, -1)))
    first_digit = 0 if first_total % 11 < 2 else 11 - (first_total % 11)
    second_total = sum(number * weight for number, weight in zip(numbers[:10], range(11, 1, -1)))
    second_digit = 0 if second_total % 11 < 2 else 11 - (second_total % 11)
    return numbers[9:] == [first_digit, second_digit]


def _format_cpf(value):
    digits = _cpf_digits(value)
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


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
        extra_kwargs = {"cpf": {"validators": []}}

    def validate_cpf(self, value):
        if not _cpf_is_valid(value):
            raise serializers.ValidationError("Informe um CPF válido.")

        digits = _cpf_digits(value)
        queryset = Motorista.objects.only("id", "cpf")
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if any(_cpf_digits(driver.cpf) == digits for driver in queryset.iterator()):
            raise serializers.ValidationError("CPF já cadastrado.")
        return _format_cpf(value)
