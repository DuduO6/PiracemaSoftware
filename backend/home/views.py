from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta

from viagens.models import Viagem
from motoristas.models import Motorista, Vale


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def home_dashboard(request):
    user = request.user

    # obtém ?dias=xx, se não houver usa 30
    dias = int(request.GET.get("dias", 30))

    hoje = timezone.now()
    limite = hoje - timedelta(days=dias)

    faturamento = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .aggregate(total=Sum('valor_total'))["total"] or 0
    )

    total_viagens = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .count()
    )

    ranking_motoristas = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .values("motorista__nome")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    total_vales_pendentes = (
        Vale.objects.filter(motorista__usuario=user, pago=False)
        .aggregate(total=Sum("valor"))["total"] or 0
    )

    motoristas_devendo = (
        Vale.objects.filter(motorista__usuario=user, pago=False)
        .values("motorista__nome")
        .annotate(total=Sum("valor"))
        .order_by("-total")
    )

    return Response({
        "dias": dias,
        "faturamento": faturamento,
        "viagens": total_viagens,
        "ranking_motoristas": list(ranking_motoristas),
        "total_vales_pendentes": total_vales_pendentes,
        "motoristas_devendo": list(motoristas_devendo)
    })