import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inteligencia_logistica", "0006_resultadoaprendizadologistico"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfiguracaoFiscal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("razao_social", models.CharField(max_length=180)),
                ("cnpj", models.CharField(max_length=14)),
                ("uf", models.CharField(max_length=2)),
                ("ambiente", models.CharField(choices=[("HOMOLOGACAO", "Homologação"), ("PRODUCAO", "Produção")], default="HOMOLOGACAO", max_length=12)),
                ("producao_liberada", models.BooleanField(default=False)),
                ("certificado_criptografado", models.BinaryField()),
                ("senha_criptografada", models.BinaryField()),
                ("certificado_nome", models.CharField(blank=True, max_length=180)),
                ("certificado_fingerprint", models.CharField(max_length=64)),
                ("certificado_cnpj", models.CharField(max_length=14)),
                ("certificado_valido_de", models.DateTimeField()),
                ("certificado_valido_ate", models.DateTimeField()),
                ("certificado_atualizado_em", models.DateTimeField(auto_now=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="configuracoes_fiscais_atualizadas", to=settings.AUTH_USER_MODEL)),
                ("empresa", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="configuracao_fiscal", to="inteligencia_logistica.empresa")),
            ],
            options={"verbose_name": "configuração fiscal MDF-e", "verbose_name_plural": "configurações fiscais MDF-e"},
        ),
        migrations.CreateModel(
            name="Manifesto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave", models.CharField(max_length=44)),
                ("numero", models.CharField(blank=True, max_length=9)),
                ("cnpj_emitente", models.CharField(max_length=14)),
                ("protocolo_autorizacao", models.CharField(max_length=15)),
                ("situacao", models.CharField(choices=[("ABERTO", "Aberto"), ("ENCERRADO", "Encerrado"), ("CANCELADO", "Cancelado"), ("A_CONFIRMAR", "Situação a confirmar"), ("DESCONHECIDO", "Situação não confirmada")], default="ABERTO", max_length=16)),
                ("listado_ultima_consulta", models.BooleanField(default=True)),
                ("data_emissao", models.DateTimeField(blank=True, null=True)),
                ("ultima_consulta_em", models.DateTimeField()),
                ("ultimo_codigo_sefaz", models.CharField(blank=True, max_length=4)),
                ("ultima_descricao_sefaz", models.CharField(blank=True, max_length=255)),
                ("protocolo_encerramento", models.CharField(blank=True, max_length=15)),
                ("encerrado_em", models.DateTimeField(blank=True, null=True)),
                ("encerramento_uf", models.CharField(blank=True, max_length=2)),
                ("encerramento_municipio_codigo", models.CharField(blank=True, max_length=7)),
                ("encerramento_municipio_nome", models.CharField(blank=True, max_length=120)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manifestos_mdfe", to="inteligencia_logistica.empresa")),
            ],
        ),
        migrations.CreateModel(
            name="ConsultaManifestos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado", models.CharField(choices=[("PROCESSANDO", "Processando"), ("SUCESSO", "Sucesso"), ("ERRO", "Erro")], default="PROCESSANDO", max_length=12)),
                ("codigo_sefaz", models.CharField(blank=True, max_length=4)),
                ("descricao_sefaz", models.CharField(blank=True, max_length=255)),
                ("categoria_erro", models.CharField(blank=True, max_length=40)),
                ("quantidade", models.PositiveIntegerField(default=0)),
                ("resposta_xml", models.TextField(blank=True)),
                ("iniciada_em", models.DateTimeField(auto_now_add=True)),
                ("finalizada_em", models.DateTimeField(blank=True, null=True)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consultas_mdfe", to="inteligencia_logistica.empresa")),
                ("solicitado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consultas_mdfe", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-iniciada_em",)},
        ),
        migrations.CreateModel(
            name="OperacaoEncerramento",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("idempotency_key", models.CharField(max_length=64)),
                ("identificador_evento", models.CharField(max_length=60)),
                ("tipo_evento", models.CharField(default="110112", max_length=6)),
                ("sequencia_evento", models.PositiveSmallIntegerField(default=1)),
                ("uf", models.CharField(max_length=2)),
                ("municipio_codigo", models.CharField(max_length=7)),
                ("municipio_nome", models.CharField(max_length=120)),
                ("data_encerramento", models.DateField()),
                ("estado", models.CharField(choices=[("PROCESSANDO", "Processando"), ("HOMOLOGADO", "Homologado"), ("REJEITADO", "Rejeitado"), ("A_CONFIRMAR", "Situação a confirmar"), ("ERRO", "Erro")], default="PROCESSANDO", max_length=16)),
                ("codigo_sefaz", models.CharField(blank=True, max_length=4)),
                ("descricao_sefaz", models.CharField(blank=True, max_length=255)),
                ("protocolo", models.CharField(blank=True, max_length=15)),
                ("registrado_em", models.DateTimeField(blank=True, null=True)),
                ("xml_evento", models.TextField(blank=True)),
                ("xml_retorno", models.TextField(blank=True)),
                ("solicitado_em", models.DateTimeField(auto_now_add=True)),
                ("finalizado_em", models.DateTimeField(blank=True, null=True)),
                ("manifesto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operacoes_encerramento", to="mdfe.manifesto")),
                ("solicitado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="encerramentos_mdfe", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-solicitado_em",)},
        ),
        migrations.AddConstraint(model_name="manifesto", constraint=models.UniqueConstraint(fields=("empresa", "chave"), name="mdfe_manifesto_empresa_chave_unica")),
        migrations.AddIndex(model_name="manifesto", index=models.Index(fields=["empresa", "situacao"], name="mdfe_manifest_emp_sit_idx")),
        migrations.AddIndex(model_name="manifesto", index=models.Index(fields=["empresa", "ultima_consulta_em"], name="mdfe_manifest_emp_cons_idx")),
        migrations.AddConstraint(model_name="operacaoencerramento", constraint=models.UniqueConstraint(fields=("manifesto", "idempotency_key"), name="mdfe_encerramento_manifesto_idempotencia_unica")),
        migrations.AddIndex(model_name="operacaoencerramento", index=models.Index(fields=["manifesto", "estado"], name="mdfe_oper_manifest_est_idx")),
    ]
