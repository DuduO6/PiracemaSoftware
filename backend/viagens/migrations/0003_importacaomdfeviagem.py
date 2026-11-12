import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inteligencia_logistica", "0007_remover_funcionalidades_inteligencia"),
        ("mdfe", "0005_manifesto_classificacao_xml"),
        ("viagens", "0002_viagem_cte_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportacaoMdfeViagem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave_mdfe", models.CharField(max_length=44)),
                ("chave_cte", models.CharField(blank=True, default=None, max_length=44, null=True)),
                ("xml_sha256", models.CharField(blank=True, max_length=64)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "criado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="importacoes_viagem_mdfe",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="importacoes_viagem_mdfe",
                        to="inteligencia_logistica.empresa",
                    ),
                ),
                (
                    "manifesto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="importacoes_viagem",
                        to="mdfe.manifesto",
                    ),
                ),
                (
                    "viagem",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="importacao_mdfe",
                        to="viagens.viagem",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="importacaomdfeviagem",
            constraint=models.UniqueConstraint(
                fields=("empresa", "chave_mdfe"),
                name="viagem_import_mdfe_empresa_chave_unica",
            ),
        ),
        migrations.AddConstraint(
            model_name="importacaomdfeviagem",
            constraint=models.UniqueConstraint(
                fields=("empresa", "chave_cte"),
                name="viagem_import_cte_empresa_chave_unica",
            ),
        ),
        migrations.AddIndex(
            model_name="importacaomdfeviagem",
            index=models.Index(fields=["empresa", "criado_em"], name="viagem_imp_empresa_data_idx"),
        ),
    ]
