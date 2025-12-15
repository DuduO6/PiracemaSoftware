from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date
from decimal import Decimal

from .models import CategoriaDespesa, Despesa, FuncionarioDespesa
from caminhoes.models import Caminhao
from .serializers import (
    CategoriaDespesaSerializer,
    DespesaSerializer,
    FuncionarioDespesaSerializer
)


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
                    "IPVA", "SEGURO", "MANUTENCAO", "ABASTECIMENTO",
                    "SALARIO", "COMISSAO", "LICENCIAMENTO", "PEDAGIO",
                    "MULTA", "OUTROS"
                ]
                for nome in categorias_padrao:
                    CategoriaDespesa.objects.create(usuario=user, nome=nome)
                qs = CategoriaDespesa.objects.filter(usuario=user)

        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class DespesaViewSet(viewsets.ModelViewSet):
    queryset = Despesa.objects.select_related('categoria', 'caminhao').all()
    serializer_class = DespesaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)
        
        # Filtros por query params
        caminhao = self.request.query_params.get('caminhao')
        categoria = self.request.query_params.get('categoria')
        tipo = self.request.query_params.get('tipo')
        status_param = self.request.query_params.get('status')
        ano = self.request.query_params.get('ano')
        mes = self.request.query_params.get('mes')
        
        # Filtro especial: mostrar apenas parcelas mensais (não mostrar despesa PAI)
        mostrar_pai = self.request.query_params.get('mostrar_pai', 'false').lower() == 'true'
        if not mostrar_pai:
            qs = qs.filter(
                Q(despesa_pai__isnull=True, tipo__in=['VARIAVEL', 'FIXA_MENSAL']) |
                Q(despesa_pai__isnull=False)  # Parcelas de FIXA_ANUAL
            )
        
        if caminhao:
            qs = qs.filter(caminhao_id=caminhao)
        
        if categoria:
            if categoria.isdigit():
                qs = qs.filter(categoria_id=int(categoria))
            else:
                qs = qs.filter(categoria__nome__iexact=categoria)
        
        if tipo:
            qs = qs.filter(tipo=tipo)
        
        if status_param:
            qs = qs.filter(status__iexact=status_param)
        
        if ano:
            try:
                ano_i = int(ano)
                qs = qs.filter(ano_referencia=ano_i)
            except ValueError:
                pass
        
        if mes:
            try:
                mes_i = int(mes)
                qs = qs.filter(mes_referencia=mes_i)
            except ValueError:
                pass
        
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        
        tipo = validated_data.get('tipo')
        
        # Se for FIXA_ANUAL, cria parcelas automaticamente
        if tipo == 'FIXA_ANUAL':
            ano = validated_data.get('ano_referencia') or timezone.now().year
            
            despesa_pai, parcelas = Despesa.criar_despesa_fixa_anual(
                usuario=user,
                categoria=validated_data['categoria'],
                descricao=validated_data['descricao'],
                valor_total=validated_data['valor_total'],
                data_inicio=serializer.validated_data["data_vencimento"],
                caminhao=validated_data.get('caminhao'),
                observacoes=validated_data.get('observacoes', '')
            )
            
            # Retorna a primeira parcela
            serializer.instance = parcelas[0] if parcelas else despesa_pai
        else:
            # Despesa VARIAVEL ou FIXA_MENSAL simples
            serializer.save(usuario=user)

    @action(detail=False, methods=['post'])
    def criar_despesa_fixa_anual(self, request):
        """
        Endpoint para criar despesa fixa anual (ex: IPVA)
        
        POST /api/despesas/despesas/criar_despesa_fixa_anual/
        Body:
        {
            "categoria_id": 1,
            "caminhao_id": 2,
            "descricao": "IPVA 2025 - Scania",
            "valor_total": "1200.00",
            "ano": 2025,
            "observacoes": "Pago em janeiro"
        }
        """
        data = request.data
        categoria_id = data.get('categoria_id')
        caminhao_id = data.get('caminhao_id')
        descricao = data.get('descricao')
        valor_total = data.get('valor_total')
        ano = data.get('ano', timezone.now().year)
        observacoes = data.get('observacoes', '')
        
        if not all([categoria_id, descricao, valor_total]):
            return Response(
                {"detail": "categoria_id, descricao e valor_total são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        categoria = get_object_or_404(CategoriaDespesa, id=categoria_id, usuario=request.user)
        caminhao = None
        if caminhao_id:
            caminhao = get_object_or_404(Caminhao, id=caminhao_id, usuario=request.user)
        
        despesa_pai, parcelas = Despesa.criar_despesa_fixa_anual(
            usuario=request.user,
            categoria=categoria,
            descricao=descricao,
            valor_total=valor_total,
            ano=int(ano),
            caminhao=caminhao,
            observacoes=observacoes
        )
        
        pai_data = DespesaSerializer(despesa_pai, context={'request': request}).data
        parcelas_data = DespesaSerializer(parcelas, many=True, context={'request': request}).data
        
        return Response({
            'despesa_pai': pai_data,
            'parcelas': parcelas_data,
            'mensagem': f'✅ Despesa criada com sucesso! Dividida em 12 parcelas de R$ {parcelas[0].valor_total}'
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def balanco_mensal(self, request):
        """
        Retorna balanço consolidado de um mês específico
        
        GET /api/despesas/despesas/balanco_mensal/?ano=2025&mes=3&caminhao=2
        
        Retorna:
        - Total de despesas do mês
        - Despesas FIXAS ANUAIS (parcelas do mês)
        - Despesas FIXAS MENSAIS (salários)
        - Despesas VARIÁVEIS
        - Detalhamento por categoria
        """
        ano = int(request.query_params.get('ano', timezone.now().year))
        mes = int(request.query_params.get('mes', timezone.now().month))
        caminhao_id = request.query_params.get('caminhao')
        
        # Query base: despesas do usuário no mês/ano
        qs = Despesa.objects.filter(
            usuario=request.user,
            ano_referencia=ano,
            mes_referencia=mes
        ).exclude(
            despesa_pai__isnull=True,
            tipo='FIXA_ANUAL'  # Exclui despesa PAI, mostra só parcelas
        )
        
        if caminhao_id:
            qs = qs.filter(caminhao_id=caminhao_id)
        
        # Totais
        total_geral = qs.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        total_pago = qs.filter(status='PAGO').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        total_pendente = qs.exclude(status='PAGO').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        
        # Por tipo
        fixas_anuais = qs.filter(tipo='FIXA_ANUAL').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        fixas_mensais = qs.filter(tipo='FIXA_MENSAL').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        variaveis = qs.filter(tipo='VARIAVEL').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        
        # Por categoria
        por_categoria = []
        categorias = CategoriaDespesa.objects.filter(usuario=request.user)
        for cat in categorias:
            total_cat = qs.filter(categoria=cat).aggregate(total=Sum('valor_total'))['total']
            if total_cat and total_cat > 0:
                por_categoria.append({
                    'categoria': cat.get_nome_display(),
                    'total': float(total_cat)
                })
        
        # Lista de despesas do mês
        despesas_lista = DespesaSerializer(
            qs.select_related('categoria', 'caminhao'),
            many=True,
            context={'request': request}
        ).data
        
        return Response({
            'ano': ano,
            'mes': mes,
            'totais': {
                'total_geral': float(total_geral),
                'total_pago': float(total_pago),
                'total_pendente': float(total_pendente),
            },
            'por_tipo': {
                'fixas_anuais': float(fixas_anuais),
                'fixas_mensais': float(fixas_mensais),
                'variaveis': float(variaveis),
            },
            'por_categoria': por_categoria,
            'despesas': despesas_lista,
            'quantidade': len(despesas_lista)
        })

    @action(detail=False, methods=['get'])
    def resumo_anual(self, request):
        """
        Retorna resumo de despesas do ano todo
        
        GET /api/despesas/despesas/resumo_anual/?ano=2025&caminhao=2
        """
        ano = int(request.query_params.get('ano', timezone.now().year))
        caminhao_id = request.query_params.get('caminhao')
        
        qs = Despesa.objects.filter(usuario=request.user, ano_referencia=ano)
        
        # Exclui despesas PAI
        qs = qs.filter(
            Q(despesa_pai__isnull=True, tipo__in=['VARIAVEL', 'FIXA_MENSAL']) |
            Q(despesa_pai__isnull=False)
        )
        
        if caminhao_id:
            qs = qs.filter(caminhao_id=caminhao_id)
        
        total = qs.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        
        # Total por mês
        por_mes = []
        for mes in range(1, 13):
            total_mes = qs.filter(mes_referencia=mes).aggregate(
                total=Sum('valor_total')
            )['total'] or Decimal('0.00')
            por_mes.append({
                'mes': mes,
                'total': float(total_mes)
            })
        
        return Response({
            'ano': ano,
            'total_anual': float(total),
            'por_mes': por_mes
        })


class FuncionarioDespesaViewSet(viewsets.ModelViewSet):
    queryset = FuncionarioDespesa.objects.all()
    serializer_class = FuncionarioDespesaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)
        
        # Filtros
        ativo = self.request.query_params.get('ativo')
        if ativo is not None:
            qs = qs.filter(ativo=ativo.lower() == 'true')
        
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=['post'])
    def gerar_salarios_ano(self, request, pk=None):
        """
        Gera 12 despesas de salário para o ano
        
        POST /api/despesas/funcionarios/{id}/gerar_salarios_ano/
        Body:
        {
            "ano": 2025,
            "categoria_salario_id": 5
        }
        """
        funcionario = self.get_object()
        ano = int(request.data.get('ano', timezone.now().year))
        categoria_id = request.data.get('categoria_salario_id')
        
        if not categoria_id:
            return Response(
                {"detail": "categoria_salario_id é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        categoria = get_object_or_404(
            CategoriaDespesa,
            id=categoria_id,
            usuario=request.user,
            nome='SALARIO'
        )
        
        despesas = funcionario.gerar_salarios_ano(ano=ano, categoria_salario=categoria)
        
        return Response({
            'mensagem': f'✅ 12 salários gerados para {funcionario.nome}',
            'despesas': DespesaSerializer(despesas, many=True, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)