from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DescontoVale, Motorista, Vale
from .serializers import MotoristaSerializer, ValeSerializer


CASAS_DECIMAIS = Decimal("0.01")


def arredondar_moeda(valor):
    return valor.quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)

class MotoristaViewSet(viewsets.ModelViewSet):
    serializer_class = MotoristaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Motorista.objects.filter(usuario=self.request.user)



class ValeViewSet(viewsets.ModelViewSet):
    serializer_class = ValeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Vale.objects.filter(motorista__usuario=self.request.user)

        motorista_id = self.request.query_params.get("motorista")
        if motorista_id:
            qs = qs.filter(motorista_id=motorista_id)

        return qs

    @action(detail=True, methods=["post"])
    def descontar(self, request, pk=None):
        vale = self.get_object()
        acerto_id = request.data.get("acerto_id")

        try:
            valor_desconto = arredondar_moeda(Decimal(str(request.data.get("valor_desconto", "0"))))
        except (TypeError, ValueError, ArithmeticError):
            return Response(
                {"detail": "Informe um valor de desconto válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if valor_desconto <= 0:
            return Response(
                {"detail": "O desconto deve ser maior que zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if vale.pago:
            return Response(
                {"detail": "Este vale já está pago."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        saldo_atual = arredondar_moeda(vale.valor)
        if valor_desconto > saldo_atual:
            return Response(
                {"detail": f"O desconto não pode ser maior que o saldo do vale: R$ {saldo_atual}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        acerto = None
        if acerto_id:
            from acertos.models import Acerto

            try:
                acerto = Acerto.objects.get(
                    id=acerto_id,
                    usuario=request.user,
                    motorista=vale.motorista,
                )
            except Acerto.DoesNotExist:
                return Response(
                    {"detail": "Acerto selecionado não encontrado para este motorista."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        restante = arredondar_moeda(saldo_atual - valor_desconto)
        quitado = restante == Decimal("0.00")

        with transaction.atomic():
            vale.valor = restante
            vale.valor_descontado = arredondar_moeda((vale.valor_descontado or Decimal("0.00")) + valor_desconto)
            vale.pago = quitado
            vale.save(update_fields=["valor", "valor_descontado", "pago"])
            DescontoVale.objects.create(
                vale=vale,
                acerto=acerto,
                valor=valor_desconto,
                saldo_antes=saldo_atual,
                saldo_depois=restante,
            )

            if acerto:
                from acertos.models import ValeAcerto

                ValeAcerto.objects.create(
                    acerto=acerto,
                    vale=vale,
                    data=vale.data,
                    valor_original=saldo_atual,
                    valor=valor_desconto,
                    valor_restante=restante,
                    quitado=quitado,
                )
                acerto.total_vales = arredondar_moeda((acerto.total_vales or Decimal("0.00")) + saldo_atual)
                acerto.desconto_vales = arredondar_moeda((acerto.desconto_vales or Decimal("0.00")) + valor_desconto)
                acerto.valor_a_receber = arredondar_moeda((acerto.valor_a_receber or Decimal("0.00")) - valor_desconto)
                acerto.save(update_fields=["total_vales", "desconto_vales", "valor_a_receber"])

        return Response(self.get_serializer(vale).data, status=status.HTTP_200_OK)
