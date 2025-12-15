from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import CategoriaDespesa, Despesa, FuncionarioDespesa
from caminhoes.models import Caminhao


class CategoriaDespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    nome_display = serializers.CharField(source='get_nome_display', read_only=True)

    class Meta:
        model = CategoriaDespesa
        fields = ['id', 'usuario', 'nome', 'nome_display', 'descricao', 'cor']
        read_only_fields = ['id']


class CaminhaoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caminhao
        fields = ['id', 'nome_conjunto', 'placa_cavalo']


class DespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    # Read-only (retorno)
    categoria = CategoriaDespesaSerializer(read_only=True)
    caminhao = CaminhaoSimpleSerializer(read_only=True)
    valor_mensal = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True,
        help_text='Valor que aparece no balanço mensal'
    )
    
    # Write-only (criação/edição)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoriaDespesa.objects.all(),
        source='categoria',
        write_only=True,
        required=True
    )
    
    caminhao_id = serializers.PrimaryKeyRelatedField(
        queryset=Caminhao.objects.all(),
        source='caminhao',
        write_only=True,
        allow_null=True,
        required=False
    )

    class Meta:
        model = Despesa
        fields = [
            'id', 'usuario',
            'categoria', 'categoria_id',
            'caminhao', 'caminhao_id',
            'descricao', 'observacoes', 
            'valor_total', 'valor_mensal',
            'tipo', 
            'ano_referencia', 'mes_referencia',
            'data_vencimento', 'data_pagamento', 
            'status', 
            'despesa_pai', 'numero_parcela', 'total_parcelas',
            'comprovante', 
            'data_cadastro', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'data_cadastro', 'data_atualizacao', 'valor_mensal']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['caminhao_id'].queryset = Caminhao.objects.filter(usuario=request.user)
            self.fields['categoria_id'].queryset = CategoriaDespesa.objects.filter(usuario=request.user)

    def validate(self, attrs):
        valor = attrs.get('valor_total')
        if valor is not None and Decimal(valor) <= Decimal('0.00'):
            raise serializers.ValidationError({
                "valor_total": "O valor deve ser maior que 0."
            })
        
        # Auto-define data de pagamento se status = PAGO
        if attrs.get('status') == 'PAGO' and not attrs.get('data_pagamento'):
            attrs['data_pagamento'] = timezone.now().date()
        
        return attrs


class FuncionarioDespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    caminhao = CaminhaoSimpleSerializer(read_only=True)
    caminhao_id = serializers.PrimaryKeyRelatedField(
        queryset=Caminhao.objects.all(),
        source='caminhao',
        write_only=True,
        allow_null=True,
        required=False
    )
    
    class Meta:
        model = FuncionarioDespesa
        fields = [
            'id', 'usuario', 'nome', 'cargo', 
            'salario_mensal', 
            'caminhao', 'caminhao_id',
            'ativo', 'data_admissao', 'data_demissao',
            'data_cadastro', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'data_cadastro', 'data_atualizacao']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['caminhao_id'].queryset = Caminhao.objects.filter(usuario=request.user)