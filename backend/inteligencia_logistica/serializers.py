from rest_framework import serializers

from .models import (ConfiguracaoLogisticaEmpresa, DecisaoLogistica, Empresa,
                     IndicadorFrete, LocalLogistico, ModeloLogisticoIA, OportunidadeFrete,
                     ParceiroFrete, PerfilEstrategia, PoloLogisticoNacional,
                     ProdutoLogistico, RotaEstrategica, TipoVeiculoPermitido)


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = "__all__"
        read_only_fields = ("usuarios",)


class TenantSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        empresa = self.context["request"].empresa_logistica
        for campo in ("parceiro", "origem", "destino", "perfil", "oportunidade_recomendada", "oportunidade_escolhida"):
            objeto = attrs.get(campo)
            if objeto is not None and getattr(objeto, "empresa_id", empresa.id) != empresa.id:
                raise serializers.ValidationError({campo: "O registro não pertence à empresa ativa."})
        return attrs


def serializer_para(modelo, campos="__all__", somente_leitura=()):
    class Gerado(TenantSerializer):
        class Meta:
            model = modelo
            fields = campos
            read_only_fields = somente_leitura
    return Gerado


LocalLogisticoSerializer = serializer_para(LocalLogistico)
ParceiroFreteSerializer = serializer_para(ParceiroFrete)
RotaEstrategicaSerializer = serializer_para(RotaEstrategica)
PerfilEstrategiaSerializer = serializer_para(PerfilEstrategia)
ConfiguracaoSerializer = serializer_para(ConfiguracaoLogisticaEmpresa)
class OportunidadeSerializer(TenantSerializer):
    valor_km_carregado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    valor_km_com_vazio = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OportunidadeFrete
        fields = "__all__"
ModeloIASerializer = serializer_para(ModeloLogisticoIA)
DecisaoSerializer = serializer_para(DecisaoLogistica, somente_leitura=("criado_por",))


class RecomendacaoSerializer(serializers.Serializer):
    oportunidade_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1)
    perfil_id = serializers.IntegerField(required=False, min_value=1)
    operacao = serializers.CharField(required=False, allow_blank=True)
    caminhao_id = serializers.IntegerField(required=False, min_value=1)
    carreta_id = serializers.IntegerField(required=False, min_value=1)
    decisao_referencia = serializers.CharField(required=False, allow_blank=True)
    tipo_veiculo = serializers.CharField(required=False, allow_blank=True)
    capacidade = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)


class PlanejamentoReposicionamentoSerializer(serializers.Serializer):
    cidade_atual = serializers.CharField(max_length=120)
    estado_atual = serializers.CharField(max_length=2, default="MG")
    destino_pessoal = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    estado_destino_pessoal = serializers.CharField(max_length=2, required=False, default="MG")
    raio_km = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=10, max_value=1000, default=150)
    modo = serializers.ChoiceField(choices=("AUTOMATICO", "MANUAL"), default="AUTOMATICO")
    regiao_busca = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    local_busca = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    estado_local_busca = serializers.CharField(max_length=2, required=False, default="MG")
    pagina_historico = serializers.IntegerField(min_value=1, default=1)
    tamanho_pagina_historico = serializers.IntegerField(min_value=1, max_value=20, default=4)


class CalculadoraFreteSerializer(serializers.Serializer):
    origem = serializers.CharField(max_length=120)
    estado_origem = serializers.CharField(max_length=2)
    destino = serializers.CharField(max_length=120)
    estado_destino = serializers.CharField(max_length=2)
    valor_frete = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    valor_pedagios_informado = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    eixos = serializers.IntegerField(min_value=2, max_value=10, default=6)


class TipoVeiculoPermitidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoVeiculoPermitido
        fields = ("tipo_veiculo", "tipo_carreta", "eixos_minimos", "eixos_maximos", "observacoes")


class ProdutoLogisticoSerializer(serializers.ModelSerializer):
    veiculos_permitidos = TipoVeiculoPermitidoSerializer(many=True, read_only=True)

    class Meta:
        model = ProdutoLogistico
        fields = "__all__"


class PoloLogisticoNacionalSerializer(serializers.ModelSerializer):
    categorias = serializers.SlugRelatedField(many=True, read_only=True, slug_field="codigo")

    class Meta:
        model = PoloLogisticoNacional
        fields = "__all__"


class IndicadorFreteSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.produto", read_only=True)

    class Meta:
        model = IndicadorFrete
        fields = "__all__"
