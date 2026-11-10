import uuid

from django.conf import settings
from django.db import models

from inteligencia_logistica.models import Empresa


class ConfiguracaoFiscal(models.Model):
    class Ambiente(models.TextChoices):
        HOMOLOGACAO = "HOMOLOGACAO", "Homologação"
        PRODUCAO = "PRODUCAO", "Produção"

    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name="configuracao_fiscal")
    razao_social = models.CharField(max_length=180)
    cnpj = models.CharField(max_length=14)
    uf = models.CharField(max_length=2)
    ambiente = models.CharField(max_length=12, choices=Ambiente.choices, default=Ambiente.HOMOLOGACAO)
    producao_liberada = models.BooleanField(default=False)
    certificado_criptografado = models.BinaryField()
    senha_criptografada = models.BinaryField()
    certificado_nome = models.CharField(max_length=180, blank=True)
    certificado_fingerprint = models.CharField(max_length=64)
    certificado_cnpj = models.CharField(max_length=14)
    certificado_valido_de = models.DateTimeField()
    certificado_valido_ate = models.DateTimeField()
    certificado_atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="configuracoes_fiscais_atualizadas"
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "configuração fiscal MDF-e"
        verbose_name_plural = "configurações fiscais MDF-e"

    def __str__(self):
        return f"{self.razao_social} - {self.get_ambiente_display()}"


class Manifesto(models.Model):
    class Situacao(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        ENCERRADO = "ENCERRADO", "Encerrado"
        CANCELADO = "CANCELADO", "Cancelado"
        A_CONFIRMAR = "A_CONFIRMAR", "Situação a confirmar"
        DESCONHECIDO = "DESCONHECIDO", "Situação não confirmada"

    class XmlStatus(models.TextChoices):
        AUSENTE = "AUSENTE", "XML ainda não consultado"
        DISPONIVEL = "DISPONIVEL", "XML armazenado"
        ERRO = "ERRO", "Falha ao obter o XML"
        REMOVIDO = "REMOVIDO", "XML removido após encerramento"

    class XmlFonte(models.TextChoices):
        PORTAL_NACIONAL = "PORTAL_NACIONAL", "Portal Nacional do MDF-e"
        IMPORTACAO_MANUAL = "IMPORTACAO_MANUAL", "Importação manual"

    class XmlClassificacao(models.TextChoices):
        NAO_AVALIADO = "NAO_AVALIADO", "Não avaliado"
        VERIFICADO = "VERIFICADO", "Conteúdo verificado"
        INFORMATIVO = "INFORMATIVO", "Somente informativo"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="manifestos_mdfe")
    chave = models.CharField(max_length=44)
    numero = models.CharField(max_length=9, blank=True)
    cnpj_emitente = models.CharField(max_length=14)
    protocolo_autorizacao = models.CharField(max_length=15)
    situacao = models.CharField(max_length=16, choices=Situacao.choices, default=Situacao.ABERTO)
    listado_ultima_consulta = models.BooleanField(default=True)
    data_emissao = models.DateTimeField(null=True, blank=True)
    ultima_consulta_em = models.DateTimeField()
    ultimo_codigo_sefaz = models.CharField(max_length=4, blank=True)
    ultima_descricao_sefaz = models.CharField(max_length=255, blank=True)
    protocolo_encerramento = models.CharField(max_length=15, blank=True)
    encerrado_em = models.DateTimeField(null=True, blank=True)
    encerramento_uf = models.CharField(max_length=2, blank=True)
    encerramento_municipio_codigo = models.CharField(max_length=7, blank=True)
    encerramento_municipio_nome = models.CharField(max_length=120, blank=True)
    xml_importado_em = models.DateTimeField(null=True, blank=True)
    xml_sha256 = models.CharField(max_length=64, blank=True)
    xml_criptografado = models.BinaryField(null=True, blank=True, editable=False)
    xml_status = models.CharField(max_length=12, choices=XmlStatus.choices, default=XmlStatus.AUSENTE)
    xml_fonte = models.CharField(max_length=20, choices=XmlFonte.choices, blank=True)
    xml_ultima_tentativa_em = models.DateTimeField(null=True, blank=True)
    xml_ultimo_erro = models.CharField(max_length=255, blank=True)
    xml_assinatura_conteudo_validada = models.BooleanField(default=False)
    xml_classificacao = models.CharField(
        max_length=12,
        choices=XmlClassificacao.choices,
        default=XmlClassificacao.NAO_AVALIADO,
    )
    destinos = models.JSONField(default=list, blank=True)
    snapshot_fiscal = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("empresa", "chave"), name="mdfe_manifesto_empresa_chave_unica")
        ]
        indexes = [
            models.Index(fields=("empresa", "situacao"), name="mdfe_manifest_emp_sit_idx"),
            models.Index(fields=("empresa", "ultima_consulta_em"), name="mdfe_manifest_emp_cons_idx"),
        ]

    def __str__(self):
        return self.chave


class ManifestoCondutor(models.Model):
    manifesto = models.ForeignKey(Manifesto, on_delete=models.CASCADE, related_name="condutores")
    nome_xml = models.CharField(max_length=150)
    cpf = models.CharField(max_length=11)
    motorista = models.ForeignKey(
        "motoristas.Motorista",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifestos_mdfe",
    )
    importado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=("manifesto", "cpf"), name="mdfe_condutor_manifesto_cpf_unico")
        ]

    def __str__(self):
        return f"{self.nome_xml} - {self.manifesto.chave}"


class ConsultaManifestos(models.Model):
    class Estado(models.TextChoices):
        PROCESSANDO = "PROCESSANDO", "Processando"
        SUCESSO = "SUCESSO", "Sucesso"
        ERRO = "ERRO", "Erro"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="consultas_mdfe")
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="consultas_mdfe"
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROCESSANDO)
    codigo_sefaz = models.CharField(max_length=4, blank=True)
    descricao_sefaz = models.CharField(max_length=255, blank=True)
    categoria_erro = models.CharField(max_length=40, blank=True)
    quantidade = models.PositiveIntegerField(default=0)
    xml_baixados = models.PositiveIntegerField(default=0)
    xml_em_cache = models.PositiveIntegerField(default=0)
    xml_erros = models.PositiveIntegerField(default=0)
    resposta_xml = models.TextField(blank=True)
    iniciada_em = models.DateTimeField(auto_now_add=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-iniciada_em",)


class OperacaoEncerramento(models.Model):
    class Estado(models.TextChoices):
        PROCESSANDO = "PROCESSANDO", "Processando"
        HOMOLOGADO = "HOMOLOGADO", "Homologado"
        REJEITADO = "REJEITADO", "Rejeitado"
        A_CONFIRMAR = "A_CONFIRMAR", "Situação a confirmar"
        ERRO = "ERRO", "Erro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifesto = models.ForeignKey(Manifesto, on_delete=models.PROTECT, related_name="operacoes_encerramento")
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="encerramentos_mdfe"
    )
    idempotency_key = models.CharField(max_length=64)
    identificador_evento = models.CharField(max_length=60)
    tipo_evento = models.CharField(max_length=6, default="110112")
    sequencia_evento = models.PositiveSmallIntegerField(default=1)
    uf = models.CharField(max_length=2)
    municipio_codigo = models.CharField(max_length=7)
    municipio_nome = models.CharField(max_length=120)
    data_encerramento = models.DateField()
    estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.PROCESSANDO)
    codigo_sefaz = models.CharField(max_length=4, blank=True)
    descricao_sefaz = models.CharField(max_length=255, blank=True)
    protocolo = models.CharField(max_length=15, blank=True)
    registrado_em = models.DateTimeField(null=True, blank=True)
    xml_evento = models.TextField(blank=True)
    xml_retorno = models.TextField(blank=True)
    solicitado_em = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-solicitado_em",)
        constraints = [
            models.UniqueConstraint(
                fields=("manifesto", "idempotency_key"), name="mdfe_encerramento_manifesto_idempotencia_unica"
            )
        ]
        indexes = [models.Index(fields=("manifesto", "estado"), name="mdfe_oper_manifest_est_idx")]

    def __str__(self):
        return f"{self.manifesto.chave} - {self.get_estado_display()}"
