from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("caminhoes", "0002_remove_caminhao_crlv_cavalo_remove_carreta_crlv"),
    ]

    operations = [
        migrations.AddField(
            model_name="caminhao",
            name="ipva_anual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="caminhao",
            name="km_estimado_ano",
            field=models.PositiveIntegerField(default=125000),
        ),
        migrations.AddField(
            model_name="caminhao",
            name="licenciamento_anual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="caminhao",
            name="percentual_valor_residual",
            field=models.DecimalField(decimal_places=2, default=30, max_digits=5),
        ),
        migrations.AddField(
            model_name="caminhao",
            name="seguro_anual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="caminhao",
            name="seguro_terceiros_anual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="caminhao",
            name="vida_util_km",
            field=models.PositiveIntegerField(default=800000),
        ),
    ]
