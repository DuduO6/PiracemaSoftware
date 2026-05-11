from rest_framework import serializers
from .models import Acerto, ItemAcerto, ValeAcerto


class ItemAcertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemAcerto
        fields = ['id', 'data', 'origem', 'destino', 'cliente', 'peso', 
                  'valor_tonelada', 'valor_total', 'teve_cte',
                  'valor_desconto_cte', 'pago']


class ValeAcertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValeAcerto
        fields = ['id', 'data', 'valor_original', 'valor', 'valor_restante', 'quitado']


class AcertoSerializer(serializers.ModelSerializer):
    motorista_nome = serializers.CharField(source='motorista.nome', read_only=True)
    regra_aplicada_nome = serializers.CharField(source='regra_aplicada.nome', read_only=True)
    itens = ItemAcertoSerializer(many=True, read_only=True)
    vales = ValeAcertoSerializer(many=True, read_only=True)

    class Meta:
        model = Acerto
        fields = ['id', 'motorista', 'motorista_nome', 'data_inicio', 'data_fim', 
                  'data_geracao', 'total_viagens', 'valor_total_viagens', 
                  'total_viagens_com_cte', 'valor_total_viagens_com_cte',
                  'total_viagens_sem_cte', 'valor_total_viagens_sem_cte',
                  'desconto_cte',
                  'total_vales', 'comissao', 'percentual_comissao', 'desconto_fixo',
                  'desconto_vales', 'valor_a_receber', 'observacoes', 'regra_aplicada',
                  'regra_aplicada_nome',
                  'itens', 'vales']
        read_only_fields = ['usuario', 'data_geracao']


class AcertoListSerializer(serializers.ModelSerializer):
    """Versão simplificada para listagem"""
    motorista_nome = serializers.CharField(source='motorista.nome', read_only=True)

    class Meta:
        model = Acerto
        fields = ['id', 'motorista', 'motorista_nome', 'data_inicio', 'data_fim', 
                  'data_geracao', 'total_viagens', 'total_viagens_com_cte',
                  'total_viagens_sem_cte', 'valor_a_receber']
