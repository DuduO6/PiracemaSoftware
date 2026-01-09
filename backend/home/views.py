from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from datetime import timedelta
from decimal import Decimal

from viagens.models import Viagem
from motoristas.models import Motorista, Vale
from despesas.models import Despesa
from caminhoes.models import Caminhao


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def home_dashboard(request):
    user = request.user

    # Obtém ?dias=xx, se não houver usa 30
    dias = int(request.GET.get("dias", 30))

    hoje = timezone.now()
    limite = hoje - timedelta(days=dias)

    # === FATURAMENTO TOTAL ===
    faturamento = float(
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .aggregate(total=Sum('valor_total'))["total"] or 0
    )

    # === TOTAL DE VIAGENS ===
    total_viagens = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .count()
    )

    # === TICKET MÉDIO (calculado no backend) ===
    ticket_medio = float(faturamento / total_viagens if total_viagens > 0 else 0)

    # === DESPESAS NO PERÍODO ===
    despesas_qs = Despesa.objects.filter(
        usuario=user,
        competencia__gte=limite.date()
    )

    despesas_total = float(despesas_qs.aggregate(total=Sum('valor'))['total'] or 0)
    despesas_pagas = float(despesas_qs.filter(status='PAGO').aggregate(total=Sum('valor'))['total'] or 0)
    despesas_pendentes = float(despesas_qs.filter(status='PENDENTE').aggregate(total=Sum('valor'))['total'] or 0)
    quantidade_despesas = despesas_qs.count()

    # === DESPESAS POR CATEGORIA (TOP 5) ===
    despesas_por_categoria = (
        despesas_qs
        .values('categoria__nome', 'categoria__cor')
        .annotate(total=Sum('valor'))
        .order_by('-total')[:5]
    )

    despesas_categoria_formatada = [
        {
            'categoria': item['categoria__nome'] or 'Sem categoria',
            'cor': item['categoria__cor'] or '#9e9e9e',
            'total': float(item['total'] or 0)
        }
        for item in despesas_por_categoria
    ]

    # === RANKING DE MOTORISTAS ===
    ranking_motoristas = list(
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .values("motorista__nome")
        .annotate(
            total=Count("id"),
            faturamento_total=Sum("valor_total")
        )
        .order_by("-total")[:10]
    )

    # Renomear chave para padrão consistente
    for item in ranking_motoristas:
        item['nome'] = item.pop('motorista__nome')
        item['faturamento_total'] = float(item['faturamento_total'] or 0)

    # === VALES PENDENTES ===
    total_vales_pendentes = float(
        Vale.objects.filter(motorista__usuario=user, pago=False)
        .aggregate(total=Sum("valor"))["total"] or 0
    )

    # === MOTORISTAS COM VALES DEVENDO ===
    motoristas_devendo = list(
        Vale.objects.filter(motorista__usuario=user, pago=False)
        .values("motorista__nome")
        .annotate(
            total=Sum("valor"),
            qtd_vales=Count("id")
        )
        .order_by("-total")
    )

    # Renomear chaves
    for item in motoristas_devendo:
        item['nome'] = item.pop('motorista__nome')
        item['total'] = float(item['total'] or 0)

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

    evolucao_formatada = [
        {
            'dia': item['dia'].strftime('%d/%m'),
            'total_viagens': item['total_viagens'],
            'faturamento': float(item['faturamento'] or 0)
        }
        for item in evolucao_diaria
    ]

    # === RESUMO POR CAMINHÃO ===
    resumo_caminhoes = []
    caminhoes = Caminhao.objects.filter(usuario=user).prefetch_related('motoristas')

    for caminhao in caminhoes:
        # Pega o motorista vinculado ao caminhão (se houver)
        motorista = caminhao.motoristas.first()  # Pega o primeiro motorista vinculado
        
        # CUSTOS (despesas vinculadas ao caminhão)
        custo_total = float(
            Despesa.objects.filter(
                usuario=user,
                caminhao=caminhao,
                competencia__gte=limite.date()
            ).aggregate(total=Sum("valor"))["total"] or 0
        )

        # FATURAMENTO (viagens do motorista do caminhão, se houver)
        faturamento_total = 0
        total_viagens_caminhao = 0
        
        if motorista:
            viagens_qs = Viagem.objects.filter(
                motorista=motorista,
                data__gte=limite
            )
            faturamento_total = float(
                viagens_qs.aggregate(total=Sum("valor_total"))["total"] or 0
            )
            total_viagens_caminhao = viagens_qs.count()

        resumo_caminhoes.append({
            "id": caminhao.id,
            "placa": caminhao.placa_cavalo or "S/P",  # ✅ campo correto
            "modelo": caminhao.nome_conjunto or "Não informado",  # ✅ campo correto
            "motorista": motorista.nome if motorista else None,
            "custo_total": custo_total,
            "faturamento_total": faturamento_total,
            "resultado": faturamento_total - custo_total,
            "total_viagens": total_viagens_caminhao,
        })

    # === ESTATÍSTICAS ADICIONAIS ===
    motoristas_ativos = (
        Viagem.objects.filter(motorista__usuario=user, data__gte=limite)
        .values('motorista')
        .distinct()
        .count()
    )

    total_motoristas = Motorista.objects.filter(usuario=user).count()

    # === COMPARAÇÃO COM PERÍODO ANTERIOR ===
    limite_anterior = limite - timedelta(days=dias)
    
    faturamento_anterior = float(
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

    def calcular_variacao(atual, anterior):
        if anterior == 0:
            return 100.0 if atual > 0 else 0.0
        return round(((atual - anterior) / anterior) * 100, 1)

    variacao_faturamento = calcular_variacao(faturamento, faturamento_anterior)
    variacao_viagens = calcular_variacao(total_viagens, viagens_anterior)

    return Response({
        "dias": dias,
        
        # Métricas principais
        "faturamento": faturamento,
        "viagens": total_viagens,
        "ticket_medio": ticket_medio,
        
        # Rankings e listas
        "ranking_motoristas": ranking_motoristas,
        "total_vales_pendentes": total_vales_pendentes,
        "motoristas_devendo": motoristas_devendo,

        # Despesas
        "despesas": {
            "total": despesas_total,
            "pagas": despesas_pagas,
            "pendentes": despesas_pendentes,
            "quantidade": quantidade_despesas,
            "por_categoria": despesas_categoria_formatada,
        },
        
        # Evolução temporal
        "evolucao_diaria": evolucao_formatada,

        # Resumo por caminhão
        "resumo_caminhoes": resumo_caminhoes,
        
        # Estatísticas adicionais
        "estatisticas": {
            "motoristas_ativos": motoristas_ativos,
            "total_motoristas": total_motoristas,
            "taxa_atividade": round((motoristas_ativos / total_motoristas * 100), 1) if total_motoristas > 0 else 0,
        },
        
        # Comparações
        "comparacao": {
            "faturamento_anterior": faturamento_anterior,
            "viagens_anterior": viagens_anterior,
            "variacao_faturamento": variacao_faturamento,
            "variacao_viagens": variacao_viagens,
        }
    })


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
    faturamento_total = float(viagens.aggregate(total=Sum('valor_total'))['total'] or 0)
    
    vales_pendentes = float(
        Vale.objects.filter(motorista=motorista, pago=False)
        .aggregate(total=Sum('valor'))['total'] or 0
    )
    
    return Response({
        "motorista": {
            "id": motorista.id,
            "nome": motorista.nome,
        },
        "periodo": dias,
        "metricas": {
            "total_viagens": total_viagens,
            "faturamento_total": faturamento_total,
            "ticket_medio": faturamento_total / total_viagens if total_viagens > 0 else 0,
            "vales_pendentes": vales_pendentes,
        }
    })