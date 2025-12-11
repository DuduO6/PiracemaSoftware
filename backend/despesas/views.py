from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date

from .models import CategoriaDespesa, Despesa, FuncionarioDespesa
from .serializers import (
    CategoriaDespesaSerializer,
    DespesaSerializer,
    FuncionarioDespesaSerializer
)

class CategoriaDespesaViewSet(viewsets.ModelViewSet):
    queryset = Despesa.objects.select_related('categoria', 'caminhao').all()
    serializer_class = DespesaSerializer


    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user and user.is_authenticated:
            # Filtra apenas parcelas (não mostra despesas PAI)
            qs = qs.filter(usuario=user, despesa_pai__isnull=True) | qs.filter(usuario=user, numero_parcela__isnull=False)
            
        caminhao = self.request.query_params.get('caminhao')
        categoria = self.request.query_params.get('categoria')
        ano = self.request.query_params.get('ano')
        mes = self.request.query_params.get('mes')
        status_param = self.request.query_params.get('status')

        if caminhao:
            qs = qs.filter(caminhao_id=caminhao)
        if categoria:
            if categoria.isdigit():
                qs = qs.filter(categoria_id=int(categoria))
            else:
                qs = qs.filter(categoria__nome__iexact=categoria)
        if status_param:
            qs = qs.filter(status__iexact=status_param)
        if ano:
            try:
                ano_i = int(ano)
                qs = qs.filter(data_vencimento__year=ano_i)
            except ValueError:
                pass
        if mes:
            try:
                mes_i = int(mes)
                qs = qs.filter(data_vencimento__month=mes_i)
            except ValueError:
                pass
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        
        # Se for tipo FIXA e tiver mais de 1 parcela, cria parcelas automaticamente
        if validated_data.get('tipo') == 'FIXA' and validated_data.get('total_parcelas', 1) > 1:
            despesa_pai, parcelas = Despesa.criar_parcelas(
                usuario=user,
                categoria=validated_data['categoria'],
                descricao=validated_data['descricao'],
                valor_total=validated_data['valor_total'],
                data_vencimento=validated_data['data_vencimento'],
                total_parcelas=validated_data['total_parcelas'],
                caminhao=validated_data.get('caminhao'),
                observacoes=validated_data.get('observacoes', ''),
                tipo=validated_data['tipo']
            )
            # Retorna a primeira parcela (para o frontend exibir)
            serializer.instance = parcelas[0] if parcelas else despesa_pai
        else:
            # Despesa normal (VARIAVEL ou RECORRENTE)
            serializer.save(usuario=user)

    def perform_update(self, serializer):
        # Ao editar, não permite mudar tipo FIXA com parcelas
        instance = self.get_object()
        if instance.despesa_pai or instance.parcelas.exists():
            raise serializers.ValidationError({
                "detail": "Não é possível editar despesas parceladas. Exclua e crie novamente."
            })
        serializer.save()

    @action(detail=False, methods=['get'])
    def resumo_mes(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total = qs.aggregate(total=Sum('valor_total'))['total'] or 0
        return Response({'total': total})


    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)

            # 🔥 Criar categorias padrão automaticamente se usuário não tiver nenhuma
            if not qs.exists():
                categorias_padrao = [
                    ("IPVA", "IPVA"),
                    ("SEGURO", "Seguro"),
                    ("MANUTENCAO", "Manutenção"),
                    ("ABASTECIMENTO", "Abastecimento"),
                    ("SALARIO", "Salário"),
                    ("COMISSAO", "Comissão"),
                    ("LICENCIAMENTO", "Licenciamento"),
                    ("PEDAGIO", "Pedágio"),
                    ("MULTA", "Multa"),
                    ("OUTROS", "Outros"),
                ]

                for cod, nome in categorias_padrao:
                    CategoriaDespesa.objects.create(
                        usuario=user,
                        nome=cod,
                        descricao=nome
                    )

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
        # por padrão, filtra pelo usuário logado
        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)
        # filtros por query params
        caminhao = self.request.query_params.get('caminhao')
        categoria = self.request.query_params.get('categoria')
        ano = self.request.query_params.get('ano')
        mes = self.request.query_params.get('mes')
        status = self.request.query_params.get('status')

        if caminhao:
            qs = qs.filter(caminhao_id=caminhao)
        if categoria:
            # aceitar tanto id quanto nome da categoria
            if categoria.isdigit():
                qs = qs.filter(categoria_id=int(categoria))
            else:
                qs = qs.filter(categoria__nome__iexact=categoria)
        if status:
            qs = qs.filter(status__iexact=status)
        if ano:
            try:
                ano_i = int(ano)
                qs = qs.filter(data_vencimento__year=ano_i)
            except ValueError:
                pass
        if mes:
            try:
                mes_i = int(mes)
                qs = qs.filter(data_vencimento__month=mes_i)
            except ValueError:
                pass
        return qs

    def perform_create(self, serializer):
        # atribui o usuário logado automaticamente
        user = self.request.user
        serializer.save(usuario=user)

    @action(detail=False, methods=['post'])
    def criar_parcelas(self, request):
        """
        Cria despesa pai + parcelas automaticamente.
        Payload exemplo:
        {
            "categoria": 1,
            "caminhao_id": 2,            # opcional
            "descricao": "IPVA 2026",
            "valor_total": "1200.00",
            "data_vencimento": "2026-01-10",
            "total_parcelas": 12
        }
        Retorna despesa pai e lista de parcelas.
        """
        data = request.data.copy()
        total_parcelas = int(data.get('total_parcelas', 12))
        categoria_id = data.get('categoria')
        caminhao_id = data.get('caminhao_id', None)
        descricao = data.get('descricao')
        valor_total = data.get('valor_total')
        data_vencimento = data.get('data_vencimento')

        if not (categoria_id and descricao and valor_total and data_vencimento):
            return Response({"detail": "categoria, descricao, valor_total e data_vencimento são obrigatórios."},
                            status=status.HTTP_400_BAD_REQUEST)

        categoria = get_object_or_404(CategoriaDespesa, id=categoria_id, usuario=request.user)
        caminhao = None
        if caminhao_id:
            caminhao = get_object_or_404(CategoriaDespesa._meta.model.__module__ and __import__('caminhao.models', fromlist=['Caminhao']) or None, id=caminhao_id)  # fallback
            # Simplificamos: importar diretamente:
            from caminhoes.models import Caminhao as _Cam
            caminhao = get_object_or_404(_Cam, id=caminhao_id, usuario=request.user)

        # chama o helper do model
        despesa_pai, parcelas = Despesa.criar_parcelas(
            usuario=request.user,
            categoria=categoria,
            descricao=descricao,
            valor_total=valor_total,
            data_vencimento= date.fromisoformat(data_vencimento) if isinstance(data_vencimento, str) else data_vencimento,
            caminhao=caminhao,
            total_parcelas=total_parcelas,
            tipo='FIXA'
        )
        pai_ser = DespesaSerializer(despesa_pai, context={'request': request})
        parc_ser = DespesaSerializer(parcelas, many=True, context={'request': request})
        return Response({'despesa_pai': pai_ser.data, 'parcelas': parc_ser.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def resumo_mes(self, request):
        """
        Retorna soma das despesas filtradas pelo mês/ano (query params mes, ano)
        Ex: /api/despesas/resumo_mes/?ano=2025&mes=1&caminhao=3
        """
        qs = self.filter_queryset(self.get_queryset())
        total = qs.aggregate(total=Sum('valor_total'))['total'] or 0
        return Response({'total': total})

class FuncionarioDespesaViewSet(viewsets.ModelViewSet):
    queryset = FuncionarioDespesa.objects.all()
    serializer_class = FuncionarioDespesaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user and user.is_authenticated:
            qs = qs.filter(usuario=user)
        return qs

    @action(detail=True, methods=['post'])
    def gerar_salarios_ano(self, request, pk=None):
        """
        Gera 12 despesas mensais para o funcionário (diluição de 13º e férias).
        Payload opcional: {"ano": 2025, "categoria_salario": ID}
        """
        func = self.get_object()
        ano = request.data.get('ano', timezone.now().year)
        categoria_id = request.data.get('categoria_salario')
        if not categoria_id:
            return Response({"detail": "categoria_salario é obrigatória."}, status=status.HTTP_400_BAD_REQUEST)
        cat = get_object_or_404(CategoriaDespesa, id=categoria_id, usuario=request.user)
        despesas = func.gerar_despesas_salariais_ano(ano=int(ano), categoria_salario=cat, usuario=request.user)
        ser = DespesaSerializer(despesas, many=True, context={'request': request})
        return Response(ser.data, status=status.HTTP_201_CREATED)
