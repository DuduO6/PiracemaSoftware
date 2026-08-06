from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inteligencia_logistica", "0005_pracapedagio_georreferencia_tarifapedagio"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResultadoAprendizadoLogistico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("aceitou_sugestao", models.BooleanField(blank=True, null=True)),
                ("features", models.JSONField(default=dict)),
                ("lucro_previsto", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("lucro_real", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("receita_real", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("custos_reais", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("km_vazio_real", models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ("tempo_espera_real_horas", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("retorno_vazio_real", models.BooleanField(blank=True, null=True)),
                ("registrado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("decisao", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="resultado_aprendizado", to="inteligencia_logistica.decisaologistica")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="inteligencia_logistica.empresa")),
                ("oportunidade", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="inteligencia_logistica.oportunidadefrete")),
            ],
            options={"indexes": [models.Index(fields=["empresa", "atualizado_em"], name="inteligenci_empresa_53c2e4_idx")]},
        ),
    ]
