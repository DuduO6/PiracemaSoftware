from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import date
from decimal import Decimal

from .models import Motorista, CategoriaDespesa, Despesa
from caminhoes.models import Caminhao
from .serializers import (
    MotoristaSerializer,
    CategoriaDespesaSerializer,
    DespesaSerializer,
)


# ==============================================================================
# VIEWSET: CATEGORIAS
# ==============================================================================

class CategoriaDespesaViewSet(viewsets.ModelViewSet):
    queryset = CategoriaDespesa.objects.all()
    serializer_class = CategoriaDespesaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)

            # Criar categorias padrão automaticamente
            if not qs.exists():
                categorias_padrao = [
                    'IPVA', 'SEGURO', 'LICENCIAMENTO', 'RASTREADOR',
                    'SALARIO', 'COMISSAO', 'MANUTENCAO', 'MULTA',
                    'GUINCHO', 'FRANQUIA_SEGURO', 'OUTROS'
                ]
                for nome in categorias_padrao:
                    CategoriaDespesa.objects.create(usuario=user, nome=nome)
                qs = CategoriaDespesa.objects.filter(usuario=user)

        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


# ==============================================================================
# VIEWSET: MOTORISTAS
# ==============================================================================

class MotoristaViewSet(viewsets.ModelViewSet):
    queryset = Motorista.objects.select_related('caminhao').all()
    serializer_class = MotoristaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)
        
        # Filtros
        ativo = self.request.query_params.get('ativo')
        if ativo is not None:
            qs = qs.filter(ativo=ativo.lower() == 'true')
        
        caminhao = self.request.query_params.get('caminhao')
        if caminhao:
            qs = qs.filter(caminhao_id=caminhao)
        
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


# ==============================================================================
# VIEWSET: DESPESAS
# ==============================================================================

class DespesaViewSet(viewsets.ModelViewSet):
    queryset = Despesa.objects.select_related(
        'categoria', 'caminhao', 'motorista'
    ).all()
    serializer_class = DespesaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)
        
        # Filtros
        caminhao = self.request.query_params.get('caminhao')
        if caminhao:
            qs = qs.filter(caminhao_id=caminhao)

        motorista = self.request.query_params.get('motorista')  # ✅ NOVO
        if motorista:
            qs = qs.filter(motorista_id=motorista)
        
        categoria = self.request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        
        ano = self.request.query_params.get('ano')
        if ano:
            qs = qs.filter(competencia__year=int(ano))
        
        mes = self.request.query_params.get('mes')
        if mes:
            qs = qs.filter(competencia__month=int(mes))
        
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
    
    @action(detail=True, methods=['post'])
    def marcar_pago(self, request, pk=None):
        """
        Marca uma despesa como paga.
        
        POST /api/despesas/despesas/{id}/marcar_pago/
        """
        despesa = self.get_object()
        despesa.marcar_pago()
        
        return Response({
            'mensagem': '✅ Despesa marcada como paga!',
            'despesa': DespesaSerializer(despesa, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def marcar_pendente(self, request, pk=None):
        """
        Marca uma despesa como pendente.
        
        POST /api/despesas/despesas/{id}/marcar_pendente/
        """
        despesa = self.get_object()
        despesa.marcar_pendente()
        
        return Response({
            'mensagem': '✅ Despesa marcada como pendente!',
            'despesa': DespesaSerializer(despesa, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def balanco_mensal(self, request):
        """
        Retorna balanço consolidado de um mês específico.
        
        GET /api/despesas/despesas/balanco_mensal/?ano=2025&mes=3&caminhao=1
        
        Retorna:
        - Total de despesas do mês
        - Total por tipo (OPERACIONAL, EVENTUAL)
        - Total por categoria
        - Total pago vs pendente
        - Lista completa de despesas
        """
        ano = int(request.query_params.get('ano', timezone.now().year))
        mes = int(request.query_params.get('mes', timezone.now().month))
        caminhao_id = request.query_params.get('caminhao')
        
        # Monta competência (primeiro dia do mês)
        competencia = date(ano, mes, 1)
        
        # Query base
        qs = Despesa.objects.filter(
            usuario=request.user,
            competencia=competencia
        ).select_related('categoria', 'caminhao', 'motorista')
        
        if caminhao_id:
            qs = qs.filter(caminhao_id=caminhao_id)
        
        # Totais gerais
        total_geral = qs.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        total_pago = qs.filter(status='PAGO').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        total_pendente = qs.filter(status='PENDENTE').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        # Por tipo de despesa
        total_operacional = qs.filter(
            tipo='OPERACIONAL'
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        total_eventual = qs.filter(
            tipo='EVENTUAL'
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        # Por categoria
        categorias_agrupadas = qs.values(
            'categoria__nome',
            'categoria__cor'
        ).annotate(
            total=Sum('valor')
        ).order_by('-total')
        
        por_categoria = [
            {
                'categoria': item['categoria__nome'],
                'cor': item['categoria__cor'],
                'total': float(item['total'])
            }
            for item in categorias_agrupadas
        ]
        
        # Lista de despesas
        despesas = DespesaSerializer(
            qs,
            many=True,
            context={'request': request}
        ).data
        
        return Response({
            'ano': ano,
            'mes': mes,
            'caminhao_id': int(caminhao_id) if caminhao_id else None,
            'totais': {
                'total_geral': float(total_geral),
                'total_pago': float(total_pago),
                'total_pendente': float(total_pendente),
            },
            'por_tipo': {
                'operacional': float(total_operacional),
                'eventual': float(total_eventual),
            },
            'por_categoria': por_categoria,
            'despesas': despesas,
            'quantidade': len(despesas)
        })
    
    @action(detail=False, methods=['get'])
    def resumo_anual(self, request):
        """
        Retorna resumo de despesas do ano todo.
        
        GET /api/despesas/despesas/resumo_anual/?ano=2025&caminhao=1
        """
        ano = int(request.query_params.get('ano', timezone.now().year))
        caminhao_id = request.query_params.get('caminhao')
        
        qs = Despesa.objects.filter(
            usuario=request.user,
            competencia__year=ano
        )
        
        if caminhao_id:
            qs = qs.filter(caminhao_id=caminhao_id)
        
        total_anual = qs.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        # Total por mês
        por_mes = []
        for mes in range(1, 13):
            competencia = date(ano, mes, 1)
            total_mes = qs.filter(
                competencia=competencia
            ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
            
            por_mes.append({
                'mes': mes,
                'competencia': competencia.strftime('%m/%Y'),
                'total': float(total_mes)
            })
        
        return Response({
            'ano': ano,
            'caminhao_id': int(caminhao_id) if caminhao_id else None,
            'total_anual': float(total_anual),
            'por_mes': por_mes
        })
    
    @action(detail=False, methods=['get'])
    def por_caminhao(self, request):
        """
        Retorna custos agrupados por caminhão em um período.
        
        GET /api/despesas/despesas/por_caminhao/?ano=2025&mes=3
        """
        ano = int(request.query_params.get('ano', timezone.now().year))
        mes = request.query_params.get('mes')
        
        qs = Despesa.objects.filter(
            usuario=request.user,
            competencia__year=ano
        )
        
        if mes:
            competencia = date(ano, int(mes), 1)
            qs = qs.filter(competencia=competencia)
        
        # Agrupa por caminhão
        por_caminhao = qs.values(
            'caminhao__id',
            'caminhao__nome_conjunto',
            'caminhao__placa_cavalo'
        ).annotate(
            total=Sum('valor'),
            quantidade_despesas=Count('id')
        ).order_by('-total')
        
        resultado = [
            {
                'caminhao_id': item['caminhao__id'],
                'nome': item['caminhao__nome_conjunto'],
                'placa': item['caminhao__placa_cavalo'],
                'total': float(item['total']),
                'quantidade_despesas': item['quantidade_despesas']
            }
            for item in por_caminhao
        ]
        
        return Response({
            'ano': ano,
            'mes': int(mes) if mes else None,
            'caminhoes': resultado
        })
    
    @action(detail=False, methods=['get'])
    def vencimentos_proximos(self, request):
        """
        Retorna despesas com vencimento nos próximos N dias.
        
        GET /api/despesas/despesas/vencimentos_proximos/?dias=7&caminhao=1
        """
        from datetime import timedelta
        
        dias = int(request.query_params.get('dias', 7))
        caminhao_id = request.query_params.get('caminhao')
        
        hoje = timezone.now().date()
        data_limite = hoje + timedelta(days=dias)
        
        qs = Despesa.objects.filter(
            usuario=request.user,
            status='PENDENTE',
            data_vencimento__isnull=False,
            data_vencimento__gte=hoje,
            data_vencimento__lte=data_limite
        ).select_related('categoria', 'caminhao').order_by('data_vencimento')
        
        if caminhao_id:
            qs = qs.filter(caminhao_id=caminhao_id)
        
        despesas = DespesaSerializer(qs, many=True, context={'request': request}).data
        
        return Response({
            'dias': dias,
            'data_inicial': hoje,
            'data_final': data_limite,
            'quantidade': len(despesas),
            'despesas': despesas
        })