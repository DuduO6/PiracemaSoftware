from datetime import timezone
from rest_framework import serializers
from decimal import Decimal
from .models import CategoriaDespesa, Despesa, FuncionarioDespesa
from caminhoes.models import Caminhao


class CategoriaDespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CategoriaDespesa
        fields = ['id', 'usuario', 'nome', 'descricao', 'cor']
        read_only_fields = ['id']

class CaminhaoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caminhao
        fields = ['id', 'nome_conjunto', 'placa_cavalo']

class DespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())

    categoria = CategoriaDespesaSerializer(read_only=True)
    caminhao = CaminhaoSimpleSerializer(read_only=True)
    
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
            'descricao', 'observacoes', 'valor_total', 'tipo', 
            'data_vencimento', 'data_pagamento', 'status', 
            'despesa_pai', 'numero_parcela', 'total_parcelas', 
            'comprovante', 'data_cadastro', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'data_cadastro', 'data_atualizacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['caminhao_id'].queryset = Caminhao.objects.filter(usuario=request.user)
            self.fields['categoria_id'].queryset = CategoriaDespesa.objects.filter(usuario=request.user)

    def validate(self, attrs):
        valor = attrs.get('valor_total')
        if valor is not None and Decimal(valor) <= Decimal('0.00'):
            raise serializers.ValidationError({"valor_total": "O valor deve ser maior que 0."})
        
        # Validação para tipo FIXA
        tipo = attrs.get('tipo', self.instance.tipo if self.instance else None)
        total_parcelas = attrs.get('total_parcelas', 1)
        
        if tipo == 'FIXA' and total_parcelas < 2:
            raise serializers.ValidationError({
                "total_parcelas": "Despesas do tipo FIXA devem ter pelo menos 2 parcelas."
            })
        
        if attrs.get('status') == 'PAGO' and not attrs.get('data_pagamento'):
            attrs['data_pagamento'] = timezone.now().date()
            
        return attrs

class FuncionarioDespesaSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = FuncionarioDespesa
        fields = [
            'id', 'usuario', 'nome', 'cargo', 'salario_base',
            'tipo_comissao', 'valor_comissao', 'ativo', 'data_admissao',
            'data_demissao', 'data_cadastro', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'data_cadastro', 'data_atualizacao']