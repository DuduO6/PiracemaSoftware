from rest_framework import serializers
from decimal import Decimal
from .models import Motorista, CategoriaDespesa, Despesa
from caminhoes.models import Caminhao


# ==============================================================================
# SERIALIZERS BASE
# ==============================================================================

class CaminhaoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caminhao
        fields = ['id', 'nome_conjunto', 'placa_cavalo']


class MotoristaSimpleSerializer(serializers.ModelSerializer):
    caminhao = CaminhaoSimpleSerializer(read_only=True)
    
    class Meta:
        model = Motorista
        fields = ['id', 'nome', 'cpf', 'caminhao']


class CategoriaDespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    nome_display = serializers.CharField(source='get_nome_display', read_only=True)

    class Meta:
        model = CategoriaDespesa
        fields = ['id', 'usuario', 'nome', 'nome_display', 'descricao', 'cor']
        read_only_fields = ['id']


# ==============================================================================
# MOTORISTA SERIALIZER
# ==============================================================================

class MotoristaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    caminhao = CaminhaoSimpleSerializer(read_only=True)
    
    # Write-only
    caminhao_id = serializers.PrimaryKeyRelatedField(
        queryset=Caminhao.objects.all(),
        source='caminhao',
        write_only=True
    )

    class Meta:
        model = Motorista
        fields = [
            'id', 'usuario', 'nome', 'cpf',
            'caminhao', 'caminhao_id',
            'salario_fixo', 'ativo',
            'data_admissao', 'data_demissao',
            'data_cadastro', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'data_cadastro', 'data_atualizacao']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['caminhao_id'].queryset = Caminhao.objects.filter(
                usuario=request.user
            )


# ==============================================================================
# DESPESA SERIALIZER
# ==============================================================================

class DespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    # Read-only (nested)
    categoria = CategoriaDespesaSerializer(read_only=True)
    caminhao = CaminhaoSimpleSerializer(read_only=True)
    motorista = MotoristaSimpleSerializer(read_only=True)
    
    # Write-only (IDs)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoriaDespesa.objects.all(),
        source='categoria',
        write_only=True,
        allow_null=False
    )
    
    caminhao_id = serializers.PrimaryKeyRelatedField(
        queryset=Caminhao.objects.all(),
        source='caminhao',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    motorista_id = serializers.PrimaryKeyRelatedField(
        queryset=Motorista.objects.all(),
        source='motorista',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # Campos calculados
    competencia_formatada = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Despesa
        fields = [
            'id', 'usuario',
            'categoria', 'categoria_id',
            'caminhao', 'caminhao_id',
            'motorista', 'motorista_id',
            'descricao', 'observacoes',
            'tipo', 'tipo_display',
            'valor',
            'competencia', 'competencia_formatada',
            'status', 'status_display',
            'data_pagamento', 'data_vencimento',
            'data_cadastro', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'data_cadastro', 'data_atualizacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            self.fields['caminhao_id'].queryset = Caminhao.objects.filter(usuario=user)
            self.fields['categoria_id'].queryset = CategoriaDespesa.objects.filter(usuario=user)
            self.fields['motorista_id'].queryset = Motorista.objects.filter(usuario=user)

    def get_competencia_formatada(self, obj):
        """Retorna competência no formato MM/YYYY."""
        return obj.competencia.strftime('%m/%Y')

    def validate(self, attrs):
        categoria = attrs.get('categoria')
        motorista = attrs.get('motorista')
        caminhao = attrs.get('caminhao')

        if categoria:
            # Para SALARIO e COMISSAO: motorista obrigatório, caminhão opcional
            if categoria.nome in ['SALARIO', 'COMISSAO']:
                if not motorista:
                    raise serializers.ValidationError({
                        'motorista_id': 'Motorista é obrigatório para salários e comissões.'
                    })
            # Para outras categorias: caminhão obrigatório
            else:
                if not caminhao:
                    raise serializers.ValidationError({
                        'caminhao_id': 'Caminhão é obrigatório para esta categoria.'
                    })

        return attrs


# ==============================================================================
# SERIALIZER PARA RESUMO/BALANÇO
# ==============================================================================

class BalancoMensalSerializer(serializers.Serializer):
    """
    Serializer para endpoint de balanço mensal.
    Retorna dados agregados + lista de despesas.
    """
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    caminhao_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Totais
    total_geral = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_pago = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_pendente = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Por tipo
    total_operacional = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_eventual = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Por categoria
    por_categoria = serializers.ListField(child=serializers.DictField())
    
    # Lista de despesas
    despesas = DespesaSerializer(many=True, read_only=True)
    quantidade = serializers.IntegerField()