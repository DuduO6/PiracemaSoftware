from rest_framework import serializers
from .models import Acerto, ItemAcerto, ValeAcerto


class ItemAcertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemAcerto
        fields = ['id', 'data', 'origem', 'destino', 'cliente', 'peso', 
                  'valor_tonelada', 'valor_total', 'pago']


class ValeAcertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValeAcerto
        fields = ['id', 'data', 'valor']


class AcertoSerializer(serializers.ModelSerializer):
    motorista_nome = serializers.CharField(source='motorista.nome', read_only=True)
    itens = ItemAcertoSerializer(many=True, read_only=True)
    vales = ValeAcertoSerializer(many=True, read_only=True)

    class Meta:
        model = Acerto
        fields = ['id', 'motorista', 'motorista_nome', 'data_inicio', 'data_fim', 
                  'data_geracao', 'total_viagens', 'valor_total_viagens', 
                  'total_vales', 'comissao', 'valor_a_receber', 'observacoes',
                  'itens', 'vales']
        read_only_fields = ['usuario', 'data_geracao']


class AcertoListSerializer(serializers.ModelSerializer):
    """Versão simplificada para listagem"""
    motorista_nome = serializers.CharField(source='motorista.nome', read_only=True)

    class Meta:
        model = Acerto
        fields = ['id', 'motorista', 'motorista_nome', 'data_inicio', 'data_fim', 
                  'data_geracao', 'total_viagens', 'valor_a_receber']