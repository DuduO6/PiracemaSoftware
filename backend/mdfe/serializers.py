from rest_framework import serializers

from .models import ConfiguracaoFiscal, ConsultaManifestos, Manifesto, ManifestoCondutor, OperacaoEncerramento
from .services.validators import normalize_cnpj, normalize_uf


class ManifestoCondutorSerializer(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()
    cpf_mascarado = serializers.SerializerMethodField()
    motorista_id = serializers.IntegerField(read_only=True, allow_null=True)
    motorista_nome = serializers.CharField(source="motorista.nome", read_only=True, allow_null=True)
    vinculado = serializers.SerializerMethodField()

    class Meta:
        model = ManifestoCondutor
        fields = ("nome", "cpf_mascarado", "motorista_id", "motorista_nome", "vinculado")

    def get_nome(self, obj):
        return obj.motorista.nome if obj.motorista_id else obj.nome_xml

    def get_cpf_mascarado(self, obj):
        return f"***.***.***-{obj.cpf[-2:]}"

    def get_vinculado(self, obj):
        return bool(obj.motorista_id)


class ManifestoSerializer(serializers.ModelSerializer):
    situacao_display = serializers.CharField(source="get_situacao_display", read_only=True)
    xml_status_display = serializers.CharField(source="get_xml_status_display", read_only=True)
    xml_classificacao_display = serializers.CharField(source="get_xml_classificacao_display", read_only=True)
    xml_somente_informativo = serializers.SerializerMethodField()
    condutores = ManifestoCondutorSerializer(many=True, read_only=True)

    class Meta:
        model = Manifesto
        fields = (
            "chave", "numero", "cnpj_emitente", "protocolo_autorizacao", "situacao", "situacao_display",
            "listado_ultima_consulta", "data_emissao", "ultima_consulta_em", "ultimo_codigo_sefaz",
            "ultima_descricao_sefaz", "protocolo_encerramento", "encerrado_em", "encerramento_uf",
            "encerramento_municipio_codigo", "encerramento_municipio_nome", "xml_importado_em",
            "xml_status", "xml_status_display", "xml_fonte", "xml_ultima_tentativa_em",
            "xml_ultimo_erro", "xml_sha256", "xml_assinatura_conteudo_validada",
            "xml_classificacao", "xml_classificacao_display", "xml_somente_informativo",
            "destinos", "condutores",
        )

    def get_xml_somente_informativo(self, obj):
        return obj.xml_classificacao == Manifesto.XmlClassificacao.INFORMATIVO


class ConsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultaManifestos
        fields = (
            "id", "estado", "codigo_sefaz", "descricao_sefaz", "categoria_erro", "quantidade",
            "xml_baixados", "xml_em_cache", "xml_erros", "iniciada_em", "finalizada_em",
        )


class OperacaoEncerramentoSerializer(serializers.ModelSerializer):
    manifesto_chave = serializers.CharField(source="manifesto.chave", read_only=True)
    manifesto_numero = serializers.CharField(source="manifesto.numero", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = OperacaoEncerramento
        fields = (
            "id", "manifesto_chave", "manifesto_numero", "identificador_evento", "tipo_evento",
            "uf", "municipio_codigo", "municipio_nome", "data_encerramento", "estado", "estado_display",
            "codigo_sefaz", "descricao_sefaz", "protocolo", "registrado_em", "solicitado_em", "finalizado_em",
        )


class EncerramentoInputSerializer(serializers.Serializer):
    uf = serializers.CharField(max_length=2)
    municipio_codigo = serializers.RegexField(r"^[0-9]{7}$")
    data_encerramento = serializers.DateField()
    confirmacao = serializers.BooleanField()

    def validate_uf(self, value):
        return normalize_uf(value)

    def validate_confirmacao(self, value):
        if not value:
            raise serializers.ValidationError("Confirme que a viagem foi concluída no local e data informados.")
        return value

    def validate(self, attrs):
        allowed = {"uf", "municipio_codigo", "data_encerramento", "confirmacao"}
        unexpected = sorted(set(self.initial_data) - allowed)
        if unexpected:
            raise serializers.ValidationError({
                "campos": (
                    "O encerramento aceita somente UF, município, data e confirmação. "
                    f"Campos não permitidos: {', '.join(unexpected)}."
                )
            })
        return attrs


class ConfiguracaoFiscalSerializer(serializers.ModelSerializer):
    certificado_configurado = serializers.SerializerMethodField()
    certificado_expirado = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracaoFiscal
        fields = (
            "razao_social", "cnpj", "uf", "ambiente", "producao_liberada", "certificado_configurado",
            "certificado_cnpj", "certificado_fingerprint", "certificado_valido_de", "certificado_valido_ate",
            "certificado_expirado", "certificado_atualizado_em", "atualizado_em",
        )
        read_only_fields = (
            "certificado_configurado", "certificado_cnpj", "certificado_fingerprint", "certificado_valido_de",
            "certificado_valido_ate", "certificado_expirado", "certificado_atualizado_em", "atualizado_em",
        )

    def get_certificado_configurado(self, obj):
        return bool(obj.certificado_criptografado)

    def get_certificado_expirado(self, obj):
        from django.utils import timezone
        return obj.certificado_valido_ate <= timezone.now()

    def validate_cnpj(self, value):
        return normalize_cnpj(value)

    def validate_uf(self, value):
        return normalize_uf(value)
