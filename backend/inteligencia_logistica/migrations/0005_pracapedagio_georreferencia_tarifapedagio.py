from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("inteligencia_logistica", "0004_configuracaologisticaempresa_tile_provider_and_more")]

    operations = [
        migrations.AddField(model_name="pracapedagio", name="categoria", field=models.CharField(blank=True, max_length=60)),
        migrations.AddField(model_name="pracapedagio", name="cidade", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="pracapedagio", name="estado", field=models.CharField(blank=True, max_length=2)),
        migrations.AddField(model_name="pracapedagio", name="km", field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
        migrations.AddField(model_name="pracapedagio", name="latitude", field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
        migrations.AddField(model_name="pracapedagio", name="longitude", field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
        migrations.AddField(model_name="pracapedagio", name="sentido", field=models.CharField(blank=True, max_length=40)),
        migrations.CreateModel(
            name="TarifaPedagio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade_eixos", models.PositiveSmallIntegerField()),
                ("valor", models.DecimalField(decimal_places=2, max_digits=10)),
                ("vigencia", models.DateField()),
                ("fonte", models.CharField(max_length=500)),
                ("versao", models.CharField(blank=True, max_length=80)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("pedagio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tarifas", to="inteligencia_logistica.pracapedagio")),
            ],
            options={
                "indexes": [models.Index(fields=["quantidade_eixos", "vigencia"], name="inteligenci_quantid_9daf1b_idx")],
                "constraints": [models.UniqueConstraint(fields=("pedagio", "quantidade_eixos", "vigencia"), name="tarifa_pedagio_eixo_vigencia_unica")],
            },
        ),
    ]
