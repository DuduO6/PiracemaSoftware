from django.contrib import admin

from .models import ConfiguracaoFiscal, ConsultaManifestos, Manifesto, ManifestoCondutor, OperacaoEncerramento


@admin.register(ConfiguracaoFiscal)
class ConfiguracaoFiscalAdmin(admin.ModelAdmin):
    list_display = ("empresa", "razao_social", "cnpj", "ambiente", "certificado_valido_ate", "atualizado_em")
    exclude = ("certificado_criptografado", "senha_criptografada")
    readonly_fields = (
        "certificado_fingerprint",
        "certificado_cnpj",
        "certificado_valido_de",
        "certificado_valido_ate",
    )


@admin.register(Manifesto)
class ManifestoAdmin(admin.ModelAdmin):
    list_display = ("chave", "empresa", "numero", "situacao", "ultima_consulta_em")
    search_fields = ("chave", "protocolo_autorizacao", "protocolo_encerramento")
    list_filter = ("situacao", "empresa")


@admin.register(ConsultaManifestos)
class ConsultaManifestosAdmin(admin.ModelAdmin):
    list_display = ("empresa", "estado", "codigo_sefaz", "quantidade", "iniciada_em")
    readonly_fields = ("resposta_xml",)


@admin.register(OperacaoEncerramento)
class OperacaoEncerramentoAdmin(admin.ModelAdmin):
    list_display = ("manifesto", "estado", "codigo_sefaz", "protocolo", "solicitado_por", "solicitado_em")
    search_fields = ("manifesto__chave", "protocolo", "identificador_evento")
    list_filter = ("estado",)
    readonly_fields = ("xml_evento", "xml_retorno")


@admin.register(ManifestoCondutor)
class ManifestoCondutorAdmin(admin.ModelAdmin):
    list_display = ("manifesto", "nome_xml", "cpf", "motorista", "importado_em")
    search_fields = ("manifesto__chave", "nome_xml", "cpf", "motorista__nome")
