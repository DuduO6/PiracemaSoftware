from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate
from datetime import timedelta, datetime

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

    # === FATURAMENTO TOTAL ===
    faturamento = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .aggregate(total=Sum('valor_total'))["total"] or 0
    )

    # === TOTAL DE VIAGENS ===
    total_viagens = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .count()
    )

    # === TICKET MÉDIO ===
    ticket_medio = faturamento / total_viagens if total_viagens > 0 else 0

    # === RANKING DE MOTORISTAS ===
    ranking_motoristas = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .values("motorista__nome")
        .annotate(
            total=Count("id"),
            faturamento_total=Sum("valor_total")
        )
        .order_by("-total")[:10]  # Top 10 motoristas
    )

    # === VALES PENDENTES ===
    total_vales_pendentes = (
        Vale.objects.filter(motorista__usuario=user, pago=False)
        .aggregate(total=Sum("valor"))["total"] or 0
    )

    # === MOTORISTAS COM VALES DEVENDO ===
    motoristas_devendo = (
        Vale.objects.filter(motorista__usuario=user, pago=False)
        .values("motorista__nome")
        .annotate(
            total=Sum("valor"),
            qtd_vales=Count("id")
        )
        .order_by("-total")
    )

    # === EVOLUÇÃO DIÁRIA (últimos 7 dias) ===
    evolucao_diaria = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=hoje - timedelta(days=7))
        .annotate(dia=TruncDate('data'))
        .values('dia')
        .annotate(
            total_viagens=Count('id'),
            faturamento=Sum('valor_total')
        )
        .order_by('dia')
    )

    # Formatar datas para o frontend
    evolucao_formatada = [
        {
            'dia': item['dia'].strftime('%d/%m'),
            'total_viagens': item['total_viagens'],
            'faturamento': float(item['faturamento']) if item['faturamento'] else 0
        }
        for item in evolucao_diaria
    ]

    # === ESTATÍSTICAS ADICIONAIS ===
    
    # Motoristas ativos (com pelo menos 1 viagem no período)
    motoristas_ativos = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .values('motorista')
        .distinct()
        .count()
    )

    # Total de motoristas cadastrados
    total_motoristas = Motorista.objects.filter(usuario=user).count()

    # Comparação com período anterior
    limite_anterior = limite - timedelta(days=dias)
    
    faturamento_anterior = (
        Viagem.objects.filter(
            motorista__usuario=user,
            data__gte=limite_anterior,
            data__lt=limite
        )
        .aggregate(total=Sum('valor_total'))["total"] or 0
    )

    viagens_anterior = (
        Viagem.objects.filter(
            motorista__usuario=user,
            data__gte=limite_anterior,
            data__lt=limite
        )
        .count()
    )

    # Cálculo de variação percentual
    def calcular_variacao(atual, anterior):
        if anterior == 0:
            return 100 if atual > 0 else 0
        return ((atual - anterior) / anterior) * 100

    variacao_faturamento = calcular_variacao(faturamento, faturamento_anterior)
    variacao_viagens = calcular_variacao(total_viagens, viagens_anterior)

    # === VIAGENS POR STATUS (se você tiver um campo status) ===
    # Adapte conforme seu modelo
    # viagens_status = (
    #     Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
    #     .values('status')
    #     .annotate(total=Count('id'))
    # )

    return Response({
        "dias": dias,
        
        # Métricas principais
        "faturamento": float(faturamento),
        "viagens": total_viagens,
        "ticket_medio": float(ticket_medio),
        
        # Rankings e listas
        "ranking_motoristas": list(ranking_motoristas),
        "total_vales_pendentes": float(total_vales_pendentes),
        "motoristas_devendo": list(motoristas_devendo),
        
        # Evolução temporal
        "evolucao_diaria": evolucao_formatada,
        
        # Estatísticas adicionais
        "estatisticas": {
            "motoristas_ativos": motoristas_ativos,
            "total_motoristas": total_motoristas,
            "taxa_atividade": round((motoristas_ativos / total_motoristas * 100), 1) if total_motoristas > 0 else 0,
        },
        
        # Comparações
        "comparacao": {
            "faturamento_anterior": float(faturamento_anterior),
            "viagens_anterior": viagens_anterior,
            "variacao_faturamento": round(variacao_faturamento, 1),
            "variacao_viagens": round(variacao_viagens, 1),
        }
    })


# === ENDPOINT ADICIONAL: DETALHES DE UM MOTORISTA ===
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def motorista_detalhes(request, motorista_id):
    """
    Retorna detalhes específicos de um motorista
    """
    user = request.user
    dias = int(request.GET.get("dias", 30))
    
    hoje = timezone.now()
    limite = hoje - timedelta(days=dias)
    
    try:
        motorista = Motorista.objects.get(id=motorista_id, usuario=user)
    except Motorista.DoesNotExist:
        return Response({"error": "Motorista não encontrado"}, status=404)
    
    viagens = Viagem.objects.filter(
        motorista=motorista,
        data__gte=limite
    )
    
    total_viagens = viagens.count()
    faturamento_total = viagens.aggregate(total=Sum('valor_total'))['total'] or 0
    
    vales_pendentes = Vale.objects.filter(
        motorista=motorista,
        pago=False
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    return Response({
        "motorista": {
            "id": motorista.id,
            "nome": motorista.nome,
        },
        "periodo": dias,
        "metricas": {
            "total_viagens": total_viagens,
            "faturamento_total": float(faturamento_total),
            "ticket_medio": float(faturamento_total / total_viagens) if total_viagens > 0 else 0,
            "vales_pendentes": float(vales_pendentes),
        }
    })